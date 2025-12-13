from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from pydantic import DirectoryPath, SecretStr, NameEmail
from typing import Any, cast

from src.utils.logging import main_logger

class EmailServiceTransientError(Exception):
    """Exception indicating a temporary, retryable failure in email sending (e.g., network error)."""
    pass

class EmailService:
    def __init__(self) -> None:
        self.conf: ConnectionConfig = ConnectionConfig(
            MAIL_USERNAME="",
            MAIL_PASSWORD=SecretStr(""),
            MAIL_FROM="no-reply@example.com",
            MAIL_PORT=25,
            MAIL_SERVER="",
            MAIL_STARTTLS=False,
            MAIL_SSL_TLS=False,
            TEMPLATE_FOLDER=Path(__file__).resolve().parents[1] / "templates",
            LOCAL_HOSTNAME="localhost",
            VALIDATE_CERTS=False,
            USE_CREDENTIALS=False,
        )
        self.mail: FastMail = FastMail(config=self.conf)
        self.template_env: Environment = Environment(
            loader=FileSystemLoader(
                searchpath=cast(DirectoryPath, self.conf.TEMPLATE_FOLDER)
            ),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_template(
        self,
        template_name: str,
        context: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    ) -> str:
        """Render a Jinja2 HTML template with context data."""
        template = self.template_env.get_template(template_name)
        return template.render(**context)

    async def __send_email(
        self,
        to_email: NameEmail,
        subject: str,
        template_name: str,
        context: dict[str, str | int | float | bool],
    ):
        body = self.render_template(template_name=template_name, context=context)
        message: MessageSchema = MessageSchema(
            subject=subject,
            recipients=[to_email],
            body=body,
            subtype=MessageType.html,
        )
        try:
            await self.mail.send_message(message=message)
        except Exception as e:
            main_logger.error(f"Error sending email to {to_email.email}: {e}")
            raise EmailServiceTransientError(f"Failed to send email: {e}")

    async def send_activate_email(
        self,
        activate_user_response: dict[str, str | dict[str, str]],
        activation_link: str,
    ):
        await self.__send_email(
            to_email=NameEmail(
                name=cast(str, activate_user_response.get("username", "")),
                email=cast(str, activate_user_response.get("email", "")),
            ),
            subject="Activate your account",
            template_name="email/activate_account_email.html",
            context={
                "username": cast(str, activate_user_response.get("username", "")),
                "activation_link": activation_link,
            },
        )

    async def send_welcome_email(
        self,
        to_email: NameEmail,
    ):
        await self.__send_email(
            to_email=to_email,
            subject="Welcome to Our Service",
            template_name="email/welcome_email.html",
            context={
                "username": to_email.name,
            },
        )

    async def send_password_reset_email(
        self,
        to_email: NameEmail,
        reset_link: str,
    ):
        await self.__send_email(
            to_email=to_email,
            subject="Password Reset Request",
            template_name="email/password_reset_email.html",
            context={
                "reset_link": reset_link,
            },
        )


email_service: EmailService = EmailService()