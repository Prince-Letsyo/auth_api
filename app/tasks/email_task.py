from asgiref.sync import async_to_sync
from pydantic import NameEmail
from app.core.celery_app import celery_app
from app.services.email_service import EmailServiceTransientError, email_service
from app.utils.logging import main_logger


@celery_app.task(  # pyright: ignore[reportUnknownMemberType, reportUntypedFunctionDecorator]
    queue="high_priority",
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
    to_email: NameEmail,
):
    try:
        async_to_sync(email_service.send_welcome_email)(to_email=to_email)
    except EmailServiceTransientError:
        main_logger.error(
            f"Email service reported a transient error for {to_email.email}. Auto-retrying..."
        )
        raise

    except Exception as exc:
        main_logger.error(f"FATAL NON-RETRYABLE ERROR sending email to {to_email.email}: {exc}")
        raise
