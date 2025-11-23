from typing import cast
from jose import ExpiredSignatureError, JWTError
from pydantic import BaseModel, EmailStr, ValidationInfo, field_validator
from sqlmodel import Field, SQLModel
from app.core.exception import AppException, UnauthorizedException
from app.schemas.user_schemas import (
    UserModel,
    UserCreate,
    UserBase,
)
from app.schemas.token_schemas import (
    AccessToken,
    ActivateAccountToken,
    RefreshToken,
    TokenModel,
)
from app.repositories.base import BaseAuthRepository
from app.utils.auth.token import jwt_auth_token
from app.utils.auth.password import password_validator


class UserResponse(UserBase):
    token: TokenModel


class ActivationEmail(BaseModel):
    email: EmailStr


class ActivateUserAccountResponse(UserBase):
    token: ActivateAccountToken


class RestPassword(SQLModel):
    password_one: str = Field(nullable=False, min_length=8)
    password_two: str = Field(nullable=False, min_length=8)

    @field_validator("password_two")
    @classmethod
    def validate_full_password(cls, v: str, info: ValidationInfo) -> str:
        """Validate password match"""
        values: dict[str, str] = info.data
        password_one: str | None = values.get("password_one")

        if not password_one or password_one != v:
            raise ValueError("Passwords do not match")
        return v


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
            payload: dict[str, str] = jwt_auth_token.decode_token(token=token)
            username: str = cast(str, payload.get("username"))
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
            data={
                "username": user.username,
                "email": user.email,
                "user_id": cast(int, user.id),
            },
        )
        return ActivateUserAccountResponse(
            username=user.username,
            email=user.email,
            token=ActivateAccountToken.model_validate(
                {"token": activate_token, "duration": activate_timestamp}
            ),
        )

    def __prepare_token_data(self, user: UserModel) -> UserResponse:
        access_token, access_timestamp = jwt_auth_token.access_token(
            data={
                "username": user.username,
                "email": user.email,
                "user_id": cast(int, user.id),
            },
        )
        refresh_token, refresh_timestamp = jwt_auth_token.refresh_token(
            data={
                "username": user.username,
                "email": user.email,
                "user_id": cast(int, user.id),
            },
        )
        return UserResponse(
            username=user.username,
            email=user.email,
            token=TokenModel(
                access_token=AccessToken.model_validate(
                    {"token": access_token, "duration": access_timestamp}
                ),
                refresh_token=RefreshToken.model_validate(
                    {"token": refresh_token, "duration": refresh_timestamp}
                ),
            ),
        )

    async def log_in(self, username: str, password: str) -> UserResponse:
        user: UserModel = await self.repository.authenticate_user(
            username=username, password=password
        )
        return self.__prepare_token_data(user)

    async def get_access_token(self, token_string: str) -> AccessToken | None:
        try:
            payload: dict[str, str] = jwt_auth_token.decode_token(token=token_string)
            if payload:
                access_token, access_timestamp = jwt_auth_token.access_token(
                    data={
                        "username": payload.get("username", ""),
                        "email": payload.get("email", ""),
                        "user_id": int(payload.get("user_id", 0)),
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

    async def password_reset(self, token: str, rest_password: RestPassword):
        try:
            payload: dict[str, str] = jwt_auth_token.decode_token(token=token)
            validation = password_validator.validate_password(
                password=rest_password.password_one,
                username=payload.get("username", ""),
                email=payload.get("email", ""),
            )
            if not validation["is_valid"]:
                raise AppException(message=cast(str, validation["errors"][0]))

            user = await self.repository.update_user_password(
                email=payload.get("email", ""), new_password=rest_password.password_one
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
