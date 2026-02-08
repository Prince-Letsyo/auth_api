import uuid
from datetime import datetime
from typing import cast

from sqlmodel import Boolean  # pyright: ignore[reportUnknownVariableType]
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, String, func

from src.core.base import TimestampMixin
from src.core.user_schemas import UserBase


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
    refresh_token_version: int = Field(
        default=0,
        nullable=False,
        description="Refresh token version for rotation",
    )
    totp_secret: str | None = Field(
        default=None,
        sa_type=String(255),
        nullable=True,
        index=False,
        description="Base32-encoded TOTP secret (16–32 chars)",
    )
    profile: "ProfileModel" = cast(
        "ProfileModel",
        Relationship(back_populates="user", sa_relationship_kwargs={"uselist": False}),
    )
    sessions: list["SessionModel"] = cast(
        list["SessionModel"],
        Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}),
    )


class ProfileModel(SQLModel, table=True):
    __tablename__ = (  # pyright: ignore[reportUnannotatedClassAttribute, reportAssignmentType]
        "profile"
    )
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    bio: str | None = Field(default=None, nullable=True)
    avatar_url: str | None = Field(default=None, nullable=True)

    user: UserModel | None = cast(UserModel, Relationship(back_populates="profile"))


class SessionModel(SQLModel, table=True):
    __tablename__ = "session"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    refresh_token_hash: str = Field(nullable=False, max_length=128)
    user_agent: str | None = Field(default=None, nullable=True, max_length=512)
    ip_address: str | None = Field(default=None, nullable=True, max_length=64)
    last_used_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    revoked_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    )
    updated_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    )

    user: UserModel | None = cast(UserModel, Relationship(back_populates="sessions"))
