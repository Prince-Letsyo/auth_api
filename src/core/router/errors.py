from pydantic import BaseModel


class ErrorResponse(BaseModel):
    success: bool = False
    error: str | dict[str, str]


class ValidationErrorResponse(BaseModel):
    success: bool = False
    errors: list[dict[str, str]]
