from typing import Any, cast

from pydantic import (BaseModel, ConfigDict, EmailStr, SecretStr,
                      ValidationInfo, field_validator)
from sqlmodel import Field  # pyright: ignore[reportUnknownVariableType]
from sqlmodel import SQLModel

from src.auth.schemas.token import (ActivateAccountToken, Temp2TAToken,
                                    TokenModel)
from src.auth.util.password import password_validator
from src.schemas.user_schemas import UserBase


class ConfirmPasswordsMixin(SQLModel):
    password_one: SecretStr = Field(nullable=False, min_length=8)
    password_two: SecretStr = Field(nullable=False, min_length=8)

    @field_validator("password_two")
    @classmethod
    def validate_confirm_passwords(cls, v: SecretStr, info: ValidationInfo):
        """Validate password match"""
        values: dict[str, SecretStr] = info.data
        password_one: SecretStr = values.get("password_one", SecretStr(""))

        if not password_one or password_one.get_secret_value() != v.get_secret_value():
            raise ValueError("Passwords do not match")
        return v


class UserCreate(ConfirmPasswordsMixin, UserBase):
    @field_validator("password_one")
    @classmethod
    def validate_full_password_one(cls, v: SecretStr, info: ValidationInfo):
        """Validate password strength and similarity"""
        values: dict[str, Any] = info.data  # pyright: ignore[reportExplicitAny]
        username: str | None = values.get("username")
        email: EmailStr | None = values.get("email")

        if not all([username, email]):
            validation_without_context: dict[str, Any] = (
                password_validator.validate_password(  # pyright: ignore[reportExplicitAny]
                    password=v.get_secret_value(), username="", email=""
                )
            )
            if not validation_without_context["is_valid"]:
                raise ValueError(
                    validation_without_context["errors"][
                        0
                    ]  # pyright: ignore[reportAny]
                )
            return v

        validation_with_context: dict[str, Any] = (
            password_validator.validate_password(  # pyright: ignore[reportExplicitAny]
                password=v.get_secret_value(),
                username=cast(str, username),
                email=cast(str, email),
            )
        )
        if not validation_with_context["is_valid"]:
            raise ValueError(
                "; ".join(
                    validation_with_context["errors"]  # pyright: ignore[reportAny]
                )
            )
        return v


class UserUpdate(UserBase):
    pass


class UserError(SQLModel):
    error: str


class AuthLogin(SQLModel):
    username: str = Field(index=True, nullable=False, unique=True)
    password: SecretStr = Field(nullable=False, min_length=8)
    model_config: ConfigDict = (  # pyright: ignore[reportIncompatibleVariableOverride]
        ConfigDict(from_attributes=True)
    )


class UserResponse(BaseModel):
    requires_2fa: bool
    token: TokenModel | Temp2TAToken


class ActivationEmail(BaseModel):
    email: EmailStr


class ActivateUserAccountResponse(UserBase):
    token: ActivateAccountToken


class PasswordResetRequest(ConfirmPasswordsMixin):
    email: EmailStr = Field(index=True, nullable=False, unique=True)


class Verify2FARequest(BaseModel):
    totp_token: str
