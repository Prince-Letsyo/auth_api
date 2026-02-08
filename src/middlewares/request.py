import uuid
from collections.abc import Awaitable
from typing import Any, Callable, cast

from fastapi import Depends, Request, status
from fastapi.responses import JSONResponse, Response
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlmodel import select
from sqlalchemy.exc import SQLAlchemyError

from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.db import get_db_session
from src.modules.auth.models import SessionModel, UserModel
from src.modules.auth.schemas.token import TokenError
from src.modules.auth.util.token import JWTPayloadWithExp, jwt_auth_token
from src.core.exceptions import UnauthorizedException
from src.core.logging import filter_sensitive as log_filter_sensitive
from src.core.logging import main_logger


SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted = headers.copy()
    for key in list(redacted.keys()):
        if key.lower() in SENSITIVE_HEADERS:
            redacted[key] = "[REDACTED]"
    return redacted


def filter_sensitive(data: dict[str, Any] | list[Any] | str) -> dict[str, Any] | list[Any] | str:
    if isinstance(data, dict):
        return log_filter_sensitive(data)
    if isinstance(data, list):
        return log_filter_sensitive(data)
    return data


async def jwt_decoder(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> JSONResponse | Response:
    token: str | None = request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        try:
            payload: dict[str, str | bool] = jwt_auth_token.decode_token(
                token=token.split(sep=" ")[1]
            )
            if payload.get("token_type") != "access":
                raise JWTError("Invalid token type")
            request.state.user = payload

        except ExpiredSignatureError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=TokenError(error="Token has expired").model_dump(),
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=TokenError(error="Invalid token").model_dump(),
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        request.state.user = None
    return await call_next(request)


async def logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if not hasattr(request.state, "req_id"):
        request.state.req_id = str(uuid.uuid4())

    # Check if request.client exists before accessing .host
    client_host = request.client.host if request.client else "unknown"

    with main_logger.contextualize(req_id=request.state.req_id, ip=client_host):
        try:
            body: Any = (
                await request.json()
                if request.headers.get("content-type") == "application/json"
                else {}
            )
            # Redact body before logging
            redacted_body = filter_sensitive(body)
            main_logger.bind(
                method=request.method,
                path=request.url.path,
                headers=redact_headers(dict[str, str](request.headers)),
            ).info(f"Incoming request: {redacted_body}")
        except Exception:
            main_logger.info("Incoming request: [Non-JSON body]")
            pass

        try:
            response: Response = await call_next(request)
            main_logger.bind(
                status_code=response.status_code,
                content_type=response.headers.get("content-type", ""),
                content_length=response.headers.get("content-length", ""),
            ).info("Response sent")
            return response
        except SQLAlchemyError as e:
            main_logger.critical(f"Database failed: {e}")
            raise
        except Exception as e:
            main_logger.exception(f"Request failed: {e}")
            raise


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # pyright: ignore[reportCallInDefaultInitializer]
):
    user = getattr(request.state, "user", None)
    if user is None:  # pyright: ignore[reportAny]
        raise UnauthorizedException(message="Unauthorized")
    session_id = user.get("sid")
    user_id = user.get("user_id")
    if not session_id or not user_id:
        raise UnauthorizedException(message="Unauthorized")

    try:
        result = await session.exec(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session_row = result.one()
        if session_row.revoked_at is not None:
            raise UnauthorizedException(message="Unauthorized")
        if session_row.user_id != int(user_id):
            raise UnauthorizedException(message="Unauthorized")

        result = await session.exec(select(UserModel).where(UserModel.id == int(user_id)))
        user_row = result.one()
        if not user_row.is_active:
            raise UnauthorizedException(message="Unauthorized")
    except Exception:
        raise UnauthorizedException(message="Unauthorized")
    return cast(JWTPayloadWithExp, user)
