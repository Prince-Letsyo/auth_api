from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.exception import AppException


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
            },
        },
    )


async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors: list[dict[str, Any]] = [  # pyright: ignore[reportExplicitAny]
        {"field": e["loc"][-1], "message": e["msg"]}
        for e in exc.errors()  # pyright: ignore[ reportAny]
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "errors": errors},
    )


async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.message},
    )


async def global_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    # Log the stack trace here
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error. Please contact support.",
        },
    )
