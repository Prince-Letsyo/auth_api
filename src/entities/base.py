from datetime import datetime
from sqlmodel import Column, DateTime, Field, func  # pyright: ignore[reportUnknownVariableType]


class TimestampMixin:
    created_at: datetime = Field(  # pyright: ignore[reportAny]
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=True
        )
    )
    updated_at: datetime = Field(  # pyright: ignore[reportAny]
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    )
