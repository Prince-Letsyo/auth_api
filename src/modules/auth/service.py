from typing import Any, cast

import qrcode
from jose import ExpiredSignatureError, JWTError
from pydantic import EmailStr

from src.modules.auth.repositories.base import BaseAuthRepository
from src.modules.auth.schemas.auth import (
    ActivateUserAccountResponse,
    PasswordResetRequest,
    UserCreate,
    UserResponse,
)
from src.modules.auth.schemas.token import (
    AccessToken,
    ActivateAccountToken,
    JWTPayload,
    RefreshToken,
    Temp2TAToken,
    TokenModel,
)
from src.modules.auth.util.mfa import generate_totp_secret, get_totp_uri, verify_totp
from src.modules.auth.util.password import password_validator
from src.modules.auth.util.token import jwt_auth_token
from src.core.exceptions import AppException, UnauthorizedException
from src.modules.auth.models import UserModel


class AuthController:
    def __init__(self, repository: BaseAuthRepository) -> None:
        self.repository: BaseAuthRepository = repository

    async def sign_up(self, user_create: UserCreate) -> ActivateUserAccountResponse:
        user: UserModel = await self.repository.create_user(user_create)
        return self.__prepare_activate_token_data(user)

    async def send_activation_email(
        self, email: EmailStr
    ) -> ActivateUserAccountResponse:
        user = await self.repository.get_user_by_email(email=email)
        if user.is_active:
            raise AppException(message="User account is already active.")
        return self.__prepare_activate_token_data(user)

    async def activate_account(self, token: str):
        try:
            payload: dict[str, str | bool] = jwt_auth_token.decode_token(token=token)
            if payload.get("token_type") != "activate":
                raise UnauthorizedException(message="Invalid token type")

            username = payload.get("username")
            if not username or not isinstance(username, str):
                raise UnauthorizedException(
                    message="Invalid token payload: missing username"
                )

            user = await self.repository.activate_user_account(username=username)
            return user
        except ExpiredSignatureError:
            raise UnauthorizedException(
                message="Token has expired",
            )
        except JWTError:
            raise UnauthorizedException(message="Invalid token")

    def __prepare_activate_token_data(
        self, user: UserModel
    ) -> ActivateUserAccountResponse:
        activate_token, activate_timestamp = jwt_auth_token.activate_token(
            data=JWTPayload(
                username=user.username, email=user.email, user_id=cast(int, user.id)
            ),
        )
        return ActivateUserAccountResponse(
            username=user.username,
            email=user.email,
            token=ActivateAccountToken.model_validate(
                {"token": activate_token, "duration": activate_timestamp}
            ),
        )

    def __prepare_token_data(self, user: UserModel, totp_provided: bool = False):
        data = JWTPayload(
            username=user.username, email=user.email, user_id=cast(int, user.id)
        )

        if user.is_2fa_enabled and not totp_provided:
            data["mfa_pending"] = True
            temp_2fa_token, temp_2fa_timestamp = jwt_auth_token.create_temp_2fa_token(
                data
            )
            token = Temp2TAToken.model_validate(
                {"token": temp_2fa_token, "duration": temp_2fa_timestamp}
            )
        else:
            access_token, access_timestamp = jwt_auth_token.access_token(data)
            refresh_token, refresh_timestamp = jwt_auth_token.refresh_token(data)
            token = TokenModel(
                access_token=AccessToken.model_validate(
                    {"token": access_token, "duration": access_timestamp}
                ),
                refresh_token=RefreshToken.model_validate(
                    {"token": refresh_token, "duration": refresh_timestamp}
                ),
            )

        return UserResponse(requires_2fa=user.is_2fa_enabled, token=token)

    async def log_in(self, username: str, password: str):
        user: UserModel = await self.repository.authenticate_user(
            username=username, password=password
        )
        return self.__prepare_token_data(user)

    async def log_in_2fa(self, token: str, totp_token: str):
        try:
            payload: dict[str, str | bool] = jwt_auth_token.decode_token(token=token)
            if payload.get("token_type") != "temp_2fa":
                raise UnauthorizedException(message="Invalid token type")
            if not payload.get("mfa_pending", False):
                raise UnauthorizedException(message="2FA is not pending for this token")
            username = payload.get("username")
            if not username or not isinstance(username, str):
                raise UnauthorizedException(
                    message="Invalid token payload: missing username"
                )

            user = await self.repository.get_user_by_username(username=username)

            if not user.is_2fa_enabled:
                raise UnauthorizedException(message="2FA is not enabled for this user")

            if user.totp_secret is None:
                raise AppException(
                    message="2FA secret is missing. Please re-enable 2FA."
                )

            if not verify_totp(
                token=totp_token, totp_secret=cast(str, user.totp_secret)
            ):
                raise UnauthorizedException(message="Invalid TOTP token")

            return self.__prepare_token_data(user, totp_provided=True)
        except ExpiredSignatureError:
            raise UnauthorizedException(
                message="Token has expired",
            )
        except JWTError:
            raise UnauthorizedException(message="Invalid token")

    async def get_access_token(self, token_string: str) -> AccessToken | None:
        try:
            payload: dict[str, str | bool] = jwt_auth_token.decode_token(
                token=token_string
            )
            if payload:
                if payload.get("token_type") != "refresh":
                    raise UnauthorizedException(message="Invalid token type")

                username = payload.get("username")
                email = payload.get("email")
                user_id = payload.get("user_id")

                if not all([username, email, user_id]):
                    raise UnauthorizedException(
                        message="Invalid token payload: missing required fields"
                    )

                access_token, access_timestamp = jwt_auth_token.access_token(
                    data={
                        "username": cast(str, username),
                        "email": cast(str, email),
                        "user_id": int(user_id),
                    },
                )
                return AccessToken.model_validate(
                    {"token": access_token, "duration": access_timestamp}
                )
        except ExpiredSignatureError:
            raise UnauthorizedException(
                message="Token has expired",
            )
        except JWTError:
            raise UnauthorizedException(message="Invalid token")

    async def password_reset(self, token: str, rest_password: PasswordResetRequest):
        try:
            payload: dict[str, Any] = jwt_auth_token.decode_token(token=token)
            if payload.get("token_type") != "activate":
                raise UnauthorizedException(message="Invalid token type")

            email = payload.get("email")
            username = payload.get("username")
            if not email or not isinstance(email, str) or not username:
                raise UnauthorizedException(
                    message="Invalid token payload: missing user info"
                )

            validation = password_validator.validate_password(
                password=rest_password.password_one.get_secret_value(),
                username=cast(str, username),
                email=cast(str, email),
            )
            if not validation["is_valid"]:
                raise AppException(message=cast(str, validation["errors"][0]))

            user = await self.repository.update_user_password(
                email=cast(str, email),
                new_password=rest_password.password_one.get_secret_value(),
            )
            return user
        except ExpiredSignatureError:
            raise UnauthorizedException(
                message="Token has expired",
            )
        except JWTError:
            raise UnauthorizedException(message="Invalid token")

    async def request_password_reset(self, email: EmailStr):
        user = await self.repository.get_user_by_email(email=email)
        return self.__prepare_activate_token_data(user)

    async def enable_2fa(self, username: str):
        user = await self.repository.get_user_by_username(username=username)
        if user.is_2fa_enabled:
            raise AppException(message="2FA is already enabled for this user.")

        totp_secret = generate_totp_secret()
        user = await self.repository.enable_2fa(
            username=user.username, totp_secret=totp_secret
        )
        uri = get_totp_uri(
            user_email=user.email, totp_secret=cast(str, user.totp_secret)
        )
        qr = qrcode.make(uri)

        import base64
        import io

        buffer = io.BytesIO()
        _ = qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {
            "secret": totp_secret,
            "qr_code": f"data:image/png;base64,{qr_base64}",
        }

    async def disable_2fa(self, username: str):
        user = await self.repository.get_user_by_username(username=username)
        if not user.is_2fa_enabled:
            raise AppException(message="2FA is not enabled for this user.")

        user = await self.repository.disable_2fa(username=user.username)
        return {"message": "2FA disabled"}
