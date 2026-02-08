from abc import ABC, abstractmethod

from pydantic import EmailStr

from src.modules.auth.schemas.auth import UserCreate
from src.modules.auth.models import UserModel


class BaseAuthRepository(ABC):
    @abstractmethod
    async def create_user(self, user_create: UserCreate) -> UserModel:
        pass

    @abstractmethod
    async def authenticate_user(self, username: str, password: str) -> UserModel:
        pass

    @abstractmethod
    async def get_user_by_username(self, username: str) -> UserModel:
        pass

    @abstractmethod
    async def get_user_by_username_any_status(self, username: str) -> UserModel:
        pass

    @abstractmethod
    async def update_refresh_token_version(
        self, username: str, new_version: int
    ) -> UserModel:
        pass

    @abstractmethod
    async def update_totp_secret(self, username: str, totp_secret: str) -> UserModel:
        pass

    @abstractmethod
    async def create_session(
        self,
        session_id: str,
        user_id: int,
        refresh_token_hash: str,
        user_agent: str | None,
        ip_address: str | None,
    ):
        pass

    @abstractmethod
    async def get_session(self, session_id: str):
        pass

    @abstractmethod
    async def update_session_token(self, session_id: str, refresh_token_hash: str):
        pass

    @abstractmethod
    async def revoke_session(self, session_id: str) -> None:
        pass

    @abstractmethod
    async def revoke_user_sessions(self, user_id: int) -> None:
        pass

    @abstractmethod
    async def list_sessions(self, user_id: int):
        pass

    @abstractmethod
    async def update_user_email(self, user_id: int, new_email: EmailStr) -> UserModel:
        pass

    @abstractmethod
    async def get_user_by_email(self, email: EmailStr) -> UserModel:
        pass

    @abstractmethod
    async def activate_user_account(self, username: str) -> UserModel:
        pass

    @abstractmethod
    async def update_user_password(
        self, email: EmailStr, new_password: str
    ) -> UserModel:
        pass

    @abstractmethod
    async def enable_2fa(self, username: str, totp_secret: str) -> UserModel:
        pass

    @abstractmethod
    async def disable_2fa(self, username: str) -> UserModel:
        pass
