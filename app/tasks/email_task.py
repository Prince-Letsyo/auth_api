from typing import cast
from asgiref.sync import async_to_sync
from pydantic import NameEmail
from app.core.celery_app import celery_app
from app.services.email_service import EmailServiceTransientError, email_service
from app.utils.logging import main_logger


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
    except EmailServiceTransientError:
        main_logger.error(
            f"Email service reported a transient error for {cast(str, activate_user_response.get("email", ""))}. Auto-retrying..."
        )
        raise

    except Exception as exc:
        main_logger.error(f"FATAL NON-RETRYABLE ERROR sending email to {cast(str, activate_user_response.get("email", ""))}: {exc}")
        raise
