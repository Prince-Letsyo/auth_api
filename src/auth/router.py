from fastapi import Depends, Request, status
from typing import cast


from src.auth.controller import AuthController
from src.config import config
from src.core.dependencies import get_auth_controller
from src.middlewares.request import get_current_user
from src.core.router.base import CustomRouter
from src.auth.schemas.token import AccessToken
from src.auth.schemas.auth import (
    ActivateUserAccountResponse,
    ActivationEmail,
    AuthLogin,
    PasswordResetRequest,
    UserCreate,
    UserResponse,
    Verify2FARequest,
)
from src.tasks.email_task import (
    log_task_success,
    send_activate_email,  # pyright: ignore[reportUnknownVariableType]
    send_password_reset_email,  # pyright: ignore[reportUnknownVariableType]
    send_welcome_email,  # pyright: ignore[reportUnknownVariableType]
)
from src.tasks.utils import (
    fire_and_forget,  # pyright: ignore[reportUnknownVariableType]
)
from src.utils import is_valid_url
from src.auth.schemas.token import JWTPayload


auth_router = CustomRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post(
    path="/sign-up", response_model=dict[str, str], status_code=status.HTTP_201_CREATED
)
async def sign_up(
    request: Request,
    user_create: UserCreate,
    auth_controller: AuthController = Depends(
        dependency=get_auth_controller
    ),  # pyright: ignore[reportCallInDefaultInitializer]
) -> dict[str, str]:
    activate_user_response: ActivateUserAccountResponse = await auth_controller.sign_up(
        user_create=user_create
    )
    FRONTEND_URL = cast(str, config.env.frontend_url)
    link = request.url_for("activate_account")
    activation_link: str = (
        f"{FRONTEND_URL+link.path if is_valid_url(url=FRONTEND_URL) else link}?token={activate_user_response.token.token}"
    )
    fire_and_forget(
        send_activate_email.s(  # pyright: ignore[reportAny, reportFunctionMemberAccess]
            activate_user_response=activate_user_response.model_dump(),
            activation_link=activation_link,
        ),
        log_task_success.s(),  # pyright: ignore[reportAny, reportFunctionMemberAccess, ]
    )
    return {
        "message": "User created successfully. Please check your email to activate your account."
    }


@auth_router.post(path="/sign-in", response_model=UserResponse)
async def sign_in(
    login_user: AuthLogin,
    auth_controller: AuthController = Depends(
        dependency=get_auth_controller
    ),  # pyright: ignore[reportCallInDefaultInitializer]
):
    return await auth_controller.log_in(
        username=login_user.username, password=login_user.password.get_secret_value()
    )


@auth_router.post(path="/sign-in-mfa", response_model=UserResponse)
async def sign_in_mfa(
    verify_2FA: Verify2FARequest,
    token: str,
    auth_controller: AuthController = Depends(
        dependency=get_auth_controller
    ),  # pyright: ignore[reportCallInDefaultInitializer]
):
    return await auth_controller.log_in_2fa(
        token=token, totp_token=verify_2FA.totp_token
    )


@auth_router.post(path="/access", response_model=AccessToken)
async def get_access_token(
    token: str,
    auth_controller: AuthController = Depends(
        dependency=get_auth_controller
    ),  # pyright: ignore[reportCallInDefaultInitializer]
):
    return await auth_controller.get_access_token(token_string=token)


@auth_router.get(
    path="/activate-account",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    name="activate_account",
)
async def activate_account(
    token: str,
    auth_controller: AuthController = Depends(
        dependency=get_auth_controller
    ),  # pyright: ignore[reportCallInDefaultInitializer]
):
    user = await auth_controller.activate_account(token=token)
    fire_and_forget(
        send_welcome_email.s(  # pyright: ignore[reportAny, reportFunctionMemberAccess]
            to_email={"name": user.username, "email": user.email},
        ),
        log_task_success.s(),  # pyright: ignore[reportAny, reportFunctionMemberAccess, ]
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
    auth_controller: AuthController = Depends(
        dependency=get_auth_controller
    ),  # pyright: ignore[reportCallInDefaultInitializer]
):
    activate_user_response: ActivateUserAccountResponse = (
        await auth_controller.send_activation_email(email=user_email.email)
    )
    FRONTEND_URL = cast(str, config.env.frontend_url)
    link = request.url_for("activate_account")
    activation_link: str = (
        f"{FRONTEND_URL+link.path if is_valid_url(url=FRONTEND_URL) else link}?token={activate_user_response.token.token}"
    )

    fire_and_forget(
        send_activate_email.s(  # pyright: ignore[reportAny, reportFunctionMemberAccess]
            activate_user_response=activate_user_response.model_dump(),
            activation_link=activation_link,
        ),
        log_task_success.s(),  # pyright: ignore[reportAny, reportFunctionMemberAccess, ]
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
    auth_controller: AuthController = Depends(
        dependency=get_auth_controller
    ),  # pyright: ignore[reportCallInDefaultInitializer]
):
    activate_user_response = await auth_controller.request_password_reset(
        email=user_email.email
    )
    FRONTEND_URL = cast(str, config.env.frontend_url)
    link = request.url_for("reset_password")
    reset_link: str = (
        f"{FRONTEND_URL+link.path if is_valid_url(url=FRONTEND_URL) else link}?token={activate_user_response.token.token}"
    )
    fire_and_forget(
        send_password_reset_email.s(  # pyright: ignore[reportAny, reportFunctionMemberAccess]
            to_email={
                "name": activate_user_response.username,
                "email": activate_user_response.email,
            },
            reset_link=reset_link,
        ),
        log_task_success.s(),  # pyright: ignore[reportAny, reportFunctionMemberAccess, ]
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
    token: str,
    auth_controller: AuthController = Depends(
        dependency=get_auth_controller
    ),  # pyright: ignore[reportCallInDefaultInitializer]
):
    _ = await auth_controller.password_reset(token=token, rest_password=rest_password)
    return {"message": "Password has been reset successfully."}


@auth_router.post(
    path="/enable-2fa",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    name="enable_2fa",
    dependencies=[Depends(dependency=get_current_user)],
)
async def enable_2fa(
    request: Request,
    auth_controller: AuthController = Depends(
        dependency=get_auth_controller
    ),  # pyright: ignore[reportCallInDefaultInitializer]
):
    payload = cast(JWTPayload, request.state.user)
    result = await auth_controller.enable_2fa(username=payload["username"])
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
    auth_controller: AuthController = Depends(
        dependency=get_auth_controller
    ),  # pyright: ignore[reportCallInDefaultInitializer]
):
    payload = cast(JWTPayload, request.state.user)
    return await auth_controller.disable_2fa(username=payload["username"])
