import json
import uuid
from fastapi import Request, status
from fastapi.responses import JSONResponse, Response
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import iterate_in_threadpool
from src.schemas.token_schemas import TokenError
from src.core.exception import UnauthorizedException
from src.utils.auth.token import JWTPayloadWithExp, jwt_auth_token
from src.utils.logging import main_logger, filter_sensitive
from typing import Any, Callable, cast
from collections.abc import Awaitable


async def jwt_decoder(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> JSONResponse | Response:
    token: str | None = request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        try:
            payload: dict[str, str | bool] = jwt_auth_token.decode_token(
                token=token.split(sep=" ")[1]
            )
            request.cookies
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
    request.state.req_id = str(uuid.uuid4())

    # Check if request.client exists before accessing .host
    client_host = request.client.host if request.client else "unknown"

    with main_logger.contextualize(req_id=request.state.req_id, ip=client_host):
        try:
            body: dict[str, str | int] = (
                await request.json()
                if request.headers.get("content-type") == "application/json"
                else {}
            )
            # Redact body before logging
            redacted_body: dict[str, str | int] | str = filter_sensitive(body.copy())
            main_logger.bind(
                method=request.method,
                path=request.url.path,
                headers=dict[str, str](request.headers),
            ).info(f"Incoming request: {redacted_body}")
        except Exception:
            main_logger.info("Incoming request: [Non-JSON body]")
            pass

        try:
            response: Response = await call_next(request)
            response_body: list[bytes] = [
                chunk
                async for chunk in response.body_iterator  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue]
            ]
            response.body_iterator = (  # pyright: ignore[reportAttributeAccessIssue]
                iterate_in_threadpool(iter(response_body))
            )
            try:
                resp_body: dict[str, str | int] | str = (
                    json.loads(s=b"".join(response_body).decode())
                    if response.headers.get("content-type") == "application/json"
                    else b"".join(response_body).decode()
                )
                redacted_resp_body: Any = []  # pyright: ignore[reportExplicitAny]
                # Redact response body
                if isinstance(resp_body, list):
                    redacted_resp_body = [
                        filter_sensitive(data=item) for item in resp_body
                    ]
                elif isinstance(resp_body, dict):
                    redacted_resp_body = filter_sensitive(data=resp_body)

            except Exception:
                redacted_resp_body = "[Non-JSON response]"
                pass
            main_logger.bind(status_code=response.status_code).info(
                f"Response sent: {redacted_resp_body}"
            )
            return response
        except SQLAlchemyError as e:
            main_logger.critical(f"Database failed: {e}")
            raise
        except Exception as e:
            main_logger.exception(f"Request failed: {e}")
            raise


async def get_current_user(request: Request):
    if request.state.user is None:  # pyright: ignore[reportAny]
        raise UnauthorizedException(message="Unauthorized")
    return cast(JWTPayloadWithExp, request.state.user)
