from typing import cast

from sqlmodel import Boolean  # pyright: ignore[reportUnknownVariableType]
from sqlmodel import Field, Relationship, SQLModel, String

from src.entities.base import TimestampMixin
from src.schemas.user_schemas import UserBase


class UserModel(TimestampMixin, UserBase, table=True):
    __tablename__ = (  # pyright: ignore[reportUnannotatedClassAttribute, reportAssignmentType]
        "user"
    )
    id: int | None = Field(default=None, primary_key=True, index=True)
    hashed_password: str = Field(nullable=False, max_length=256)
    is_active: bool = Field(default=False, nullable=False)
    is_2fa_enabled: bool = Field(
        sa_type=Boolean,
        default=False,
        nullable=False,
        description="Whether 2FA is enabled for this user",
    )
    totp_secret: str | None = Field(
        default=None,
        sa_type=String(32),
        nullable=True,
        index=False,
        description="Base32-encoded TOTP secret (16–32 chars)",
    )
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
