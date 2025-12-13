from typing import cast
from asgiref.sync import async_to_sync
from celery import shared_task  # pyright: ignore[reportUnknownVariableType, reportMissingTypeStubs]
from pydantic import NameEmail
from src.core.celery_app import celery_app
from src.services.email_service import EmailServiceTransientError, email_service
from src.utils.logging import main_logger



@shared_task
def log_task_success(result:dict[str,str]):
    """Logs the successful completion of a linked task."""
    main_logger.info(f"✅ Linked task finished successfully. Result: {result}")
    # This is where you could trigger a database update or another non-critical task.

@shared_task(bind=True)  # pyright: ignore[reportAny]
def log_task_failure(self, task_id):  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType, reportUnusedParameter]
    """
    Logs the failure of any task that links to it using link_error.
    The task ID, exception, and traceback are automatically passed by Celery.
    """
    main_logger.error(f"❌ Celery Task Failure Handler Triggered")
    main_logger.error(f"   Task ID: {task_id}")



@celery_app.task(  # pyright: ignore[reportUnknownMemberType, reportUntypedFunctionDecorator]
    bind=True,
    acks_late=True,
    max_retries=5,
    autoretry_for=(EmailServiceTransientError,),
    retry_backoff=True,
    retry_jitter=True,
    default_retry_delay=1,
)
def send_welcome_email(
    self,# pyright: ignore[reportUnknownParameterType, reportMissingParameterType, reportUnusedParameter]
    to_email: dict[str,str],
):
    name_email=NameEmail(name=to_email.get("name",""), email=to_email.get("email",""))
    try:
        async_to_sync(email_service.send_welcome_email)(to_email=name_email)
        return {"type": "welcome", "email": name_email.email}
    except EmailServiceTransientError:
        main_logger.error(
            f"Email service reported a transient error for {name_email.email}. Auto-retrying..."
        )
        raise

    except Exception as exc:
        main_logger.error(f"FATAL NON-RETRYABLE ERROR sending email to {name_email.email}: {exc}")
        raise
    
    
@celery_app.task(  # pyright: ignore[reportUnknownMemberType, reportUntypedFunctionDecorator]
    bind=True,
    acks_late=True,
    max_retries=5,
    autoretry_for=(EmailServiceTransientError,),
    retry_backoff=True,
    retry_jitter=True,
    default_retry_delay=1,
)
def send_password_reset_email(
    self,# pyright: ignore[reportUnknownParameterType, reportMissingParameterType, reportUnusedParameter]
    to_email: dict[str,str],
    reset_link: str,
):
    name_email=NameEmail(name=to_email.get("name",""), email=to_email.get("email",""))
    try:
        async_to_sync(email_service.send_password_reset_email)(to_email=name_email, reset_link=reset_link)
        return {"type": "password_reset", "email": name_email.email}
    except EmailServiceTransientError:
        main_logger.error(
            f"Email service reported a transient error for {name_email.email}. Auto-retrying..."
        )
        raise

    except Exception as exc:
        main_logger.error(f"FATAL NON-RETRYABLE ERROR sending email to {name_email.email}: {exc}")
        raise

@celery_app.task(  # pyright: ignore[reportUnknownMemberType, reportUntypedFunctionDecorator]
    bind=True,
    acks_late=True,
    max_retries=5,
    autoretry_for=(EmailServiceTransientError,),
    retry_backoff=True,
    retry_jitter=True,
    default_retry_delay=1,
)
def send_activate_email(
    self,# pyright: ignore[reportUnknownParameterType, reportMissingParameterType, reportUnusedParameter]
    activate_user_response: dict[str, str | dict[str, str]],
    activation_link: str,
):
    try:
        async_to_sync(email_service.send_activate_email)(
            activate_user_response=activate_user_response, 
            activation_link=activation_link)
        return {"type": "activation", "email": activate_user_response.get("email")}
    except EmailServiceTransientError:
        main_logger.error(
            f"Email service reported a transient error for {cast(str, activate_user_response.get("email", ""))}. Auto-retrying..."
        )
        raise

    except Exception as exc:
        main_logger.error(f"FATAL NON-RETRYABLE ERROR sending email to {cast(str, activate_user_response.get("email", ""))}: {exc}")
        raise
