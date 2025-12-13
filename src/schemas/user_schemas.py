from sqlmodel import (
    SQLModel,
    Field,  # pyright: ignore[reportUnknownVariableType]
)
from pydantic import ConfigDict, EmailStr


class UserBase(SQLModel):
    username: str = Field(index=True, nullable=False, unique=True)
    email: EmailStr = Field(index=True, nullable=False, unique=True)

    model_config: ConfigDict = (  # pyright: ignore[reportIncompatibleVariableOverride]
        ConfigDict(from_attributes=True)
    )

