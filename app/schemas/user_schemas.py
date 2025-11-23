from typing import Any, cast
from sqlmodel import Relationship, SQLModel, Field
from pydantic import ConfigDict, EmailStr, ValidationInfo, field_validator

from app.schemas.base import TimestampMixin
from app.utils.auth.password import password_validator


class UserBase(SQLModel):
    username: str = Field(index=True, nullable=False, unique=True)
    email: EmailStr = Field(index=True, nullable=False, unique=True)

    model_config: ConfigDict = (  # pyright: ignore[reportIncompatibleVariableOverride]
        ConfigDict(from_attributes=True)
    )


class ConfirmPasswords(SQLModel):
    password_one: str = Field(nullable=False, min_length=8)
    password_two: str = Field(nullable=False, min_length=8)

    @field_validator("password_two")
    @classmethod
    def validate_confirm_passwords(cls, v: str, info: ValidationInfo) -> str:
        """Validate password match"""
        values: dict[str, str] = info.data
        password_one: str | None = values.get("password_one")

        if not password_one or password_one != v:
            raise ValueError("Passwords do not match")
        return v


class UserCreate(ConfirmPasswords):
    @field_validator("password_one")
    @classmethod
    def validate_full_password_one(cls, v: str, info: ValidationInfo) -> str:
        """Validate password strength and similarity"""
        values: dict[str, Any] = info.data  # pyright: ignore[reportExplicitAny]
        username: str | None = values.get("username")
        email: EmailStr | None = values.get("email")

        if not all([username, email]):
            validation_without_context: dict[str, Any] = (  # pyright: ignore[reportExplicitAny]
                password_validator.validate_password(  
                    password=v, username="", email=""
                )
            )
            if not validation_without_context["is_valid"]:
                raise ValueError(
                    validation_without_context["errors"][0]  # pyright: ignore[reportAny]
                )  
            return v

        validation_with_context: dict[str, Any] = (  # pyright: ignore[reportExplicitAny]
            password_validator.validate_password(  
                password=v, username=cast(str, username), email=cast(str, email)
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


class UserModel(TimestampMixin, UserBase, table=True):
    __tablename__ = (  # pyright: ignore[reportUnannotatedClassAttribute, reportAssignmentType]
        "user"
    )
    id: int | None = Field(default=None, primary_key=True, index=True)
    hashed_password: str = Field(nullable=False, max_length=256)
    is_active: bool = Field(default=False, nullable=False)

    profile: "ProfileModel" = cast(
        "ProfileModel",
        Relationship(back_populates="user", sa_relationship_kwargs={"uselist": False}),
    )


class ProfileModel(SQLModel, table=True):
    __tablename__ = (  # pyright: ignore[reportUnannotatedClassAttribute, reportAssignmentType]
        "profile"
    )
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    bio: str = Field(default=False, nullable=True)
    avatar_url: str = Field(default=False, nullable=True)

    user: UserModel | None = cast(UserModel, Relationship(back_populates="profile"))


class UserError(SQLModel):
    error: str


class AuthLogin(SQLModel):
    username: str = Field(index=True, nullable=False, unique=True)
    password: str = Field(nullable=False, min_length=8)
    model_config: ConfigDict = (  # pyright: ignore[reportIncompatibleVariableOverride]
        ConfigDict(from_attributes=True)
    )
