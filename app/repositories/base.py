from abc import ABC, abstractmethod
from pydantic import EmailStr

from app.schemas.user_schemas import UserModel, UserCreate


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
    async def enable_2fa(
        self, username: str, totp_secret: str
    ) -> UserModel:
        pass
    
    @abstractmethod
    async def disable_2fa(
        self, username: str
    ) -> UserModel:
        pass
