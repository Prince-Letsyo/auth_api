from fastapi import Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from src.modules.auth.service import AuthService
from src.modules.auth.repositories.repository import AuthRepository
from src.core.db import get_db_session
from src.core.exceptions import UnauthorizedException
from src.config import config


async def get_auth_service(
    session: AsyncSession = Depends(dependency=get_db_session),  # pyright: ignore[reportCallInDefaultInitializer]
) -> AuthService:
    """Dependency to get the AuthService."""
    repository = AuthRepository(db=session)
    return AuthService(repository=repository)


async def require_admin_api_key(request: Request):
    api_key = config.env.api_key
    if not api_key:
        raise UnauthorizedException(message="Unauthorized")
    header_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if header_key != api_key:
        raise UnauthorizedException(message="Unauthorized")
