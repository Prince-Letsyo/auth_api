from typing import ClassVar, Self
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.controllers.auth_controller import AuthController
from app.core.db import get_db_session
from app.repositories.auth_repository import AuthRepository
from app.repositories.base import BaseAuthRepository


class DependencyContainer:
    _instance: ClassVar["DependencyContainer | None"] = None
    auth_repository: BaseAuthRepository | None = None
    auth_controller: AuthController | None = None

    def __new__(cls) -> Self | "DependencyContainer":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self, db: AsyncSession) -> None:
        if self.auth_repository is None:
            self.auth_repository = AuthRepository(db)
            self.auth_controller = AuthController(self.auth_repository)

    async def cleanup(self):
        self.auth_repository = None
        self.auth_controller = None


# Global container instance
dependency_container: DependencyContainer = DependencyContainer()


async def get_auth_controller(
    session: AsyncSession = Depends(
        dependency=get_db_session
    ),  # pyright: ignore[reportCallInDefaultInitializer]
) -> AuthController:
    await dependency_container.initialize(db=session)
    if dependency_container.auth_controller is None:
        raise ValueError(
            "AuthController not initialized. Ensure repositories are set up first."
        )
    controller = dependency_container.auth_controller
    await dependency_container.cleanup()
    return controller
