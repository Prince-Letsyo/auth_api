from typing import cast

from fastapi import Depends, Request, status

from src.config import config
from src.core.dependencies import get_auth_service, require_admin_api_key
from src.core.router.base import CustomRouter
from src.middlewares.request import get_current_user
from src.modules.auth.schemas.auth import (
    ActivateUserAccountResponse,
    ActivationEmail,
    AuthLogin,
    ChangeEmailRequest,
    LogoutRequest,
    PasswordResetRequest,
    SessionResponse,
    TokenRequest,
    UserCreate,
    UserResponse,
    Verify2FARequest,
)
from src.modules.auth.schemas.token import JWTPayload, TokenModel
from src.modules.auth.service import AuthService
from src.shared.utils.alembic_utils import is_valid_url
from src.tasks.email import (  # pyright: ignore[reportUnknownVariableType]
    log_task_failure,
    log_task_success,
    send_activate_email,
    send_password_reset_email,
    send_welcome_email,
)


def fire_and_forget(task, *args, **kwargs):
    """Simple wrapper for fire and forget tasks."""
    return task.apply_async(
        args=args,
        kwargs=kwargs,
        link=log_task_success.s(),
        link_error=log_task_failure.s(),
    )


auth_router = CustomRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post(
    path="/sign-up", response_model=dict[str, str], status_code=status.HTTP_201_CREATED
)
async def sign_up(
    request: Request,
    user_create: UserCreate,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
) -> dict[str, str]:
    activate_user_response: ActivateUserAccountResponse = await auth_service.sign_up(
        user_create=user_create
    )
    FRONTEND_URL = cast(str, config.env.frontend_url)
    link = request.url_for("activate_account")
    activation_link: str = f"{FRONTEND_URL + link.path if is_valid_url(url=FRONTEND_URL) else link}?token={activate_user_response.token.token}"
    fire_and_forget(
        send_activate_email.s(  # pyright: ignore[reportAny, reportFunctionMemberAccess]
            activate_user_response=activate_user_response.model_dump(),
            activation_link=activation_link,
        )
    )
    return {
        "message": "User created successfully. Please check your email to activate your account."
    }


@auth_router.post(path="/sign-in", response_model=UserResponse)
async def sign_in(
    request: Request,
    login_user: AuthLogin,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    return await auth_service.log_in(
        username=login_user.username,
        password=login_user.password.get_secret_value(),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )


@auth_router.post(path="/sign-in-mfa", response_model=UserResponse)
async def sign_in_mfa(
    request: Request,
    verify_2FA: Verify2FARequest,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    return await auth_service.log_in_2fa(
        token=verify_2FA.token,
        totp_token=verify_2FA.totp_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )


@auth_router.post(path="/access", response_model=TokenModel)
async def get_access_token(
    token_request: TokenRequest,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    return await auth_service.get_access_token(token_string=token_request.token)


@auth_router.get(
    path="/activate-account",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    name="activate_account",
)
async def activate_account(
    token: str,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    user = await auth_service.activate_account(token=token)
    fire_and_forget(
        send_welcome_email.s(  # pyright: ignore[reportAny, reportFunctionMemberAccess]
            to_email={"name": user.username, "email": user.email},
        )
    )
    return {"message": "Account activated successfully. You can now log in."}


@auth_router.post(
    path="/send-activation-email",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    name="send_activation_email",
)
async def send_activation_email(
    request: Request,
    user_email: ActivationEmail,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    activate_user_response: ActivateUserAccountResponse = (
        await auth_service.send_activation_email(email=user_email.email)
    )
    FRONTEND_URL = cast(str, config.env.frontend_url)
    link = request.url_for("activate_account")
    activation_link: str = f"{FRONTEND_URL + link.path if is_valid_url(url=FRONTEND_URL) else link}?token={activate_user_response.token.token}"

    fire_and_forget(
        send_activate_email.s(  # pyright: ignore[reportAny, reportFunctionMemberAccess]
            activate_user_response=activate_user_response.model_dump(),
            activation_link=activation_link,
        )
    )
    return {"message": "Activation email sent successfully. Please check your email."}


@auth_router.post(
    path="/request-password-reset",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    name="request_password_reset",
)
async def request_password_reset(
    request: Request,
    user_email: ActivationEmail,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    reset_response = await auth_service.request_password_reset(email=user_email.email)
    FRONTEND_URL = cast(str, config.env.frontend_url)
    link = request.url_for("reset_password")
    reset_link: str = f"{FRONTEND_URL + link.path if is_valid_url(url=FRONTEND_URL) else link}?token={reset_response.token.token}"
    fire_and_forget(
        send_password_reset_email.s(  # pyright: ignore[reportAny, reportFunctionMemberAccess]
            to_email={
                "name": reset_response.username,
                "email": reset_response.email,
            },
            reset_link=reset_link,
        )
    )
    return {"message": "A password reset link has been sent to your email."}


@auth_router.post(
    path="/reset-password",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    name="reset_password",
)
async def reset_password(
    rest_password: PasswordResetRequest,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    _ = await auth_service.password_reset(
        token=rest_password.token, rest_password=rest_password
    )
    return {"message": "Password has been reset successfully."}


@auth_router.post(
    path="/logout",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    name="logout",
)
async def logout(
    logout_request: LogoutRequest,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    return await auth_service.logout(refresh_token=logout_request.token)


@auth_router.post(
    path="/logout-all",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    name="logout_all",
    dependencies=[Depends(dependency=get_current_user)],
)
async def logout_all(
    request: Request,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    payload = cast(JWTPayload, request.state.user)
    return await auth_service.logout_all(user_id=cast(int, payload["user_id"]))


@auth_router.get(
    path="/sessions",
    response_model=list[SessionResponse],
    status_code=status.HTTP_200_OK,
    name="list_sessions",
    dependencies=[Depends(dependency=get_current_user)],
)
async def list_sessions(
    request: Request,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    payload = cast(JWTPayload, request.state.user)
    return await auth_service.list_sessions(user_id=cast(int, payload["user_id"]))


@auth_router.post(
    path="/change-email",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    name="change_email",
    dependencies=[Depends(dependency=get_current_user)],
)
async def change_email(
    request: Request,
    change_request: ChangeEmailRequest,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    payload = cast(JWTPayload, request.state.user)
    return await auth_service.change_email(
        username=cast(str, payload["username"]),
        new_email=str(change_request.new_email),
        password=change_request.password.get_secret_value(),
    )


@auth_router.post(
    path="/admin/revoke-sessions/{user_id}",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    name="admin_revoke_sessions",
    dependencies=[Depends(dependency=require_admin_api_key)],
)
async def admin_revoke_sessions(
    user_id: int,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    return await auth_service.admin_revoke_sessions(user_id=user_id)


@auth_router.post(
    path="/enable-2fa",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    name="enable_2fa",
    dependencies=[Depends(dependency=get_current_user)],
)
async def enable_2fa(
    request: Request,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    payload = cast(JWTPayload, request.state.user)
    result = await auth_service.enable_2fa(username=payload["username"])
    return {**result, "message": "2FA enabled. Scan with your app."}


@auth_router.post(
    path="/disable-2fa",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    name="disable_2fa",
    dependencies=[Depends(dependency=get_current_user)],
)
async def disable_2fa(
    request: Request,
    auth_service: AuthService = Depends(dependency=get_auth_service),  # pyright: ignore[reportCallInDefaultInitializer]
):
    payload = cast(JWTPayload, request.state.user)
    return await auth_service.disable_2fa(username=payload["username"])
