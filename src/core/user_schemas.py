from pydantic import ConfigDict, EmailStr
from sqlmodel import Field  # pyright: ignore[reportUnknownVariableType]
from sqlmodel import SQLModel


class UserBase(SQLModel):
    username: str = Field(index=True, nullable=False, unique=True)
    email: EmailStr = Field(index=True, nullable=False, unique=True)

    model_config: ConfigDict = (  # pyright: ignore[reportIncompatibleVariableOverride]
        ConfigDict(from_attributes=True)
    )
