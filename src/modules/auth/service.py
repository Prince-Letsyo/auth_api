import base64
import hmac
import io
import uuid
from typing import Any, cast

import qrcode
from jose import ExpiredSignatureError, JWTError
from pydantic import EmailStr

from src.modules.auth.repositories.base import BaseAuthRepository
from src.modules.auth.schemas.auth import (
    ActivateUserAccountResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    UserCreate,
    UserResponse,
)
from src.modules.auth.schemas.token import (
    AccessToken,
    ActivateAccountToken,
    JWTPayload,
    PasswordResetToken,
    RefreshToken,
    Temp2TAToken,
    TokenModel,
)
from src.modules.auth.util.mfa import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_totp_secret,
    get_totp_uri,
    verify_totp,
)
from src.modules.auth.util.password import password_validator
from src.modules.auth.util.token import hash_token, jwt_auth_token
from src.core.exceptions import AppException, NotFoundException, UnauthorizedException
from src.modules.auth.models import UserModel


class AuthService:
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

    def __prepare_password_reset_token_data(
        self, user: UserModel
    ) -> PasswordResetResponse:
        reset_token, reset_timestamp = jwt_auth_token.password_reset_token(
            data=JWTPayload(
                username=user.username, email=user.email, user_id=cast(int, user.id)
            ),
        )
        return PasswordResetResponse(
            username=user.username,
            email=user.email,
            token=PasswordResetToken.model_validate(
                {"token": reset_token, "duration": reset_timestamp}
            ),
        )

    async def __issue_tokens(
        self,
        user: UserModel,
        session_id: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenModel:
        data = JWTPayload(
            username=user.username,
            email=user.email,
            user_id=cast(int, user.id),
            sid=session_id,
        )
        access_token, access_timestamp = jwt_auth_token.access_token(data)
        refresh_token, refresh_timestamp = jwt_auth_token.refresh_token(
            {**data, "jti": str(uuid.uuid4())}
        )
        refresh_hash = hash_token(refresh_token)
        await self.repository.create_session(
            session_id=session_id,
            user_id=cast(int, user.id),
            refresh_token_hash=refresh_hash,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        return TokenModel(
            access_token=AccessToken.model_validate(
                {"token": access_token, "duration": access_timestamp}
            ),
            refresh_token=RefreshToken.model_validate(
                {"token": refresh_token, "duration": refresh_timestamp}
            ),
        )

    def __prepare_mfa_token(self, user: UserModel) -> UserResponse:
        data = JWTPayload(
            username=user.username,
            email=user.email,
            user_id=cast(int, user.id),
        )
        data["mfa_pending"] = True
        temp_2fa_token, temp_2fa_timestamp = jwt_auth_token.create_temp_2fa_token(data)
        token = Temp2TAToken.model_validate(
            {"token": temp_2fa_token, "duration": temp_2fa_timestamp}
        )
        return UserResponse(requires_2fa=True, token=token)

    async def log_in(
        self,
        username: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ):
        user: UserModel = await self.repository.authenticate_user(
            username=username, password=password
        )
        if user.is_2fa_enabled:
            return self.__prepare_mfa_token(user)
        session_id = str(uuid.uuid4())
        token = await self.__issue_tokens(
            user=user,
            session_id=session_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        return UserResponse(requires_2fa=False, token=token)

    async def log_in_2fa(
        self,
        token: str,
        totp_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ):
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

            try:
                decrypted_secret = decrypt_totp_secret(cast(str, user.totp_secret))
                legacy_plaintext = False
            except ValueError:
                decrypted_secret = cast(str, user.totp_secret)
                legacy_plaintext = True

            if not verify_totp(token=totp_token, totp_secret=decrypted_secret):
                raise UnauthorizedException(message="Invalid TOTP token")

            if legacy_plaintext:
                encrypted_secret = encrypt_totp_secret(decrypted_secret)
                await self.repository.update_totp_secret(
                    username=user.username, totp_secret=encrypted_secret
                )

            session_id = str(uuid.uuid4())
            token = await self.__issue_tokens(
                user=user,
                session_id=session_id,
                user_agent=user_agent,
                ip_address=ip_address,
            )
            return UserResponse(requires_2fa=False, token=token)
        except ExpiredSignatureError:
            raise UnauthorizedException(
                message="Token has expired",
            )
        except JWTError:
            raise UnauthorizedException(message="Invalid token")

    async def get_access_token(self, token_string: str) -> TokenModel | None:
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
                session_id = payload.get("sid")

                if not all([username, email, user_id, session_id]):
                    raise UnauthorizedException(
                        message="Invalid token payload: missing required fields"
                    )

                try:
                    user = await self.repository.get_user_by_username_any_status(
                        username=cast(str, username)
                    )
                except NotFoundException:
                    raise UnauthorizedException(message="Invalid token")

                if not user.is_active:
                    raise UnauthorizedException(message="User account is not active")

                if user.id != int(user_id) or user.email != email:
                    raise UnauthorizedException(message="Invalid token")

                try:
                    session = await self.repository.get_session(
                        session_id=cast(str, session_id)
                    )
                except NotFoundException:
                    raise UnauthorizedException(message="Invalid token")

                if session.revoked_at is not None:
                    raise UnauthorizedException(message="Invalid token")

                if session.user_id != cast(int, user.id):
                    raise UnauthorizedException(message="Invalid token")

                refresh_hash = hash_token(token_string)
                if not hmac.compare_digest(refresh_hash, session.refresh_token_hash):
                    raise UnauthorizedException(message="Invalid token")

                access_token, access_timestamp = jwt_auth_token.access_token(
                    data={
                        "username": cast(str, username),
                        "email": cast(str, email),
                        "user_id": int(user_id),
                        "sid": cast(str, session_id),
                    },
                )
                refresh_token, refresh_timestamp = jwt_auth_token.refresh_token(
                    data={
                        "username": cast(str, username),
                        "email": cast(str, email),
                        "user_id": int(user_id),
                        "sid": cast(str, session_id),
                        "jti": str(uuid.uuid4()),
                    },
                )
                await self.repository.update_session_token(
                    session_id=cast(str, session_id),
                    refresh_token_hash=hash_token(refresh_token),
                )
                return TokenModel(
                    access_token=AccessToken.model_validate(
                        {"token": access_token, "duration": access_timestamp}
                    ),
                    refresh_token=RefreshToken.model_validate(
                        {"token": refresh_token, "duration": refresh_timestamp}
                    ),
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
            if payload.get("token_type") != "password_reset":
                raise UnauthorizedException(message="Invalid token type")

            email = payload.get("email")
            username = payload.get("username")
            if not email or not isinstance(email, str) or not username:
                raise UnauthorizedException(
                    message="Invalid token payload: missing user info"
                )
            if rest_password.email != email:
                raise UnauthorizedException(
                    message="Invalid token payload: email mismatch"
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
            await self.repository.revoke_user_sessions(user_id=cast(int, user.id))
            return user
        except ExpiredSignatureError:
            raise UnauthorizedException(
                message="Token has expired",
            )
        except JWTError:
            raise UnauthorizedException(message="Invalid token")

    async def request_password_reset(self, email: EmailStr):
        user = await self.repository.get_user_by_email(email=email)
        return self.__prepare_password_reset_token_data(user)

    async def enable_2fa(self, username: str):
        user = await self.repository.get_user_by_username(username=username)
        if user.is_2fa_enabled:
            raise AppException(message="2FA is already enabled for this user.")

        totp_secret = generate_totp_secret()
        encrypted_secret = encrypt_totp_secret(totp_secret)
        user = await self.repository.enable_2fa(
            username=user.username, totp_secret=encrypted_secret
        )
        uri = get_totp_uri(user_email=user.email, totp_secret=totp_secret)
        qr = qrcode.make(uri)

        buffer = io.BytesIO()
        _ = qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        await self.repository.revoke_user_sessions(user_id=cast(int, user.id))
        return {
            "secret": totp_secret,
            "qr_code": f"data:image/png;base64,{qr_base64}",
        }

    async def disable_2fa(self, username: str):
        user = await self.repository.get_user_by_username(username=username)
        if not user.is_2fa_enabled:
            raise AppException(message="2FA is not enabled for this user.")

        user = await self.repository.disable_2fa(username=user.username)
        await self.repository.revoke_user_sessions(user_id=cast(int, user.id))
        return {"message": "2FA disabled"}

    async def logout(self, refresh_token: str):
        try:
            payload: dict[str, str | bool] = jwt_auth_token.decode_token(
                token=refresh_token
            )
            if payload.get("token_type") != "refresh":
                raise UnauthorizedException(message="Invalid token type")

            session_id = payload.get("sid")
            username = payload.get("username")
            email = payload.get("email")
            user_id = payload.get("user_id")
            if not all([session_id, username, email, user_id]):
                raise UnauthorizedException(
                    message="Invalid token payload: missing required fields"
                )

            try:
                user = await self.repository.get_user_by_username_any_status(
                    username=cast(str, username)
                )
            except NotFoundException:
                raise UnauthorizedException(message="Invalid token")

            if user.id != int(user_id) or user.email != email:
                raise UnauthorizedException(message="Invalid token")

            try:
                session = await self.repository.get_session(
                    session_id=cast(str, session_id)
                )
            except NotFoundException:
                raise UnauthorizedException(message="Invalid token")

            if session.revoked_at is not None:
                return {"message": "Logged out"}

            refresh_hash = hash_token(refresh_token)
            if not hmac.compare_digest(refresh_hash, session.refresh_token_hash):
                raise UnauthorizedException(message="Invalid token")

            await self.repository.revoke_session(session_id=cast(str, session_id))
            return {"message": "Logged out"}
        except ExpiredSignatureError:
            raise UnauthorizedException(
                message="Token has expired",
            )
        except JWTError:
            raise UnauthorizedException(message="Invalid token")

    async def logout_all(self, user_id: int):
        await self.repository.revoke_user_sessions(user_id=user_id)
        return {"message": "Logged out from all sessions"}

    async def list_sessions(self, user_id: int):
        sessions = await self.repository.list_sessions(user_id=user_id)
        return [
            {
                "id": session.id,
                "user_agent": session.user_agent,
                "ip_address": session.ip_address,
                "created_at": session.created_at,
                "last_used_at": session.last_used_at,
                "revoked_at": session.revoked_at,
            }
            for session in sessions
        ]

    async def change_email(self, username: str, new_email: str, password: str):
        user = await self.repository.get_user_by_username_any_status(username=username)
        if not password_validator.verify_password(
            plain_password=password, hashed_password=user.hashed_password
        ):
            raise UnauthorizedException(message="Incorrect username or password")
        user = await self.repository.update_user_email(
            user_id=cast(int, user.id), new_email=new_email
        )
        await self.repository.revoke_user_sessions(user_id=cast(int, user.id))
        return {"message": "Email updated successfully"}

    async def admin_revoke_sessions(self, user_id: int):
        await self.repository.revoke_user_sessions(user_id=user_id)
        return {"message": "User sessions revoked"}
