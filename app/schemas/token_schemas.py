from datetime import datetime
from sqlmodel import Column, SQLModel, Field,DateTime  # pyright: ignore[reportUnknownVariableType]
from pydantic import ConfigDict


class AccessToken(SQLModel):
    token: str = Field(nullable=False)
    duration:datetime=Field(sa_column=Column(DateTime(timezone=True), nullable=False))

    model_config: ConfigDict = ConfigDict(from_attributes=True)  # pyright: ignore[reportIncompatibleVariableOverride]

class RefreshToken(SQLModel):
    token: str = Field(nullable=False)
    duration:datetime=Field(sa_column=Column(DateTime(timezone=True), nullable=False))

    model_config: ConfigDict = ConfigDict(from_attributes=True)  # pyright: ignore[reportIncompatibleVariableOverride]
class ActivateAccountToken(SQLModel):
    token: str = Field(nullable=False)
    duration:datetime=Field(sa_column=Column(DateTime(timezone=True), nullable=False))

    model_config: ConfigDict = ConfigDict(from_attributes=True)  # pyright: ignore[reportIncompatibleVariableOverride]

class TokenBase(SQLModel):
    access_token: str = Field(nullable=False)
    token_type: str = Field(nullable=False)

    model_config: ConfigDict = ConfigDict(from_attributes=True)  # pyright: ignore[reportIncompatibleVariableOverride]


class TokenModel(SQLModel):
    access_token: AccessToken
    refresh_token: RefreshToken
    model_config: ConfigDict = ConfigDict(from_attributes=True)  # pyright: ignore[reportIncompatibleVariableOverride]


class TokenError(SQLModel):
    error: str


class TokenData(SQLModel):
    username: str | None = None
    scopes: list[str] = []
    user_id: int | None = None
    exp: int | None = None
    model_config: ConfigDict = ConfigDict(from_attributes=True)  # pyright: ignore[reportIncompatibleVariableOverride]
