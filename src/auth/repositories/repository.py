from pydantic import EmailStr
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import ScalarResult
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlmodel import select
from typing import override

from src.entities.user_entity import UserModel
from src.auth.schemas.auth import UserCreate
from src.utils.auth.password import password_validator
from src.core.exception import AppException, ConflictException, NotFoundException
from src.auth.repositories.base import BaseAuthRepository


class AuthRepository(BaseAuthRepository):
    def __init__(self, db: AsyncSession) -> None:
        self.db: AsyncSession = db

    @override
    async def create_user(self, user_create: UserCreate) -> UserModel:
        try:
            user_dict = user_create.model_dump(exclude={"password_one", "password_two"})
            user_dict["hashed_password"] = password_validator.get_password_hash(
                user_create.password_one.get_secret_value()
            )

            user = UserModel(**user_dict)  # pyright: ignore[reportAny]
            self.db.add(instance=user)
            await self.db.commit()
            await self.db.refresh(instance=user)
            return user
        except IntegrityError as e:
            raise ConflictException(
                message="User already exist",
            )
        except Exception as e:
            raise e

    @override
    async def activate_user_account(self, username: str) -> UserModel:
        try:
            result: ScalarResult[UserModel] = await self.db.exec(
                select(UserModel).where(UserModel.username == username)
            )
            user: UserModel = result.one()
            if user.is_active:
                raise AppException(message="User account is already active.")
            user.is_active = True
            self.db.add(instance=user)
            await self.db.commit()
            await self.db.refresh(instance=user)
            return user
        except NoResultFound as e:
            raise NotFoundException(
                message=f"User with username '{username}' does not exist",
            )
        except Exception as e:
            raise e

    @override
    async def authenticate_user(self, username: str, password: str) -> UserModel:
        try:
            user: UserModel = await self.get_user_by_username(username)
            if not password_validator.verify_password(
                plain_password=password, hashed_password=user.hashed_password
            ):
                raise AppException(message="Incorrect username or password")
            return user
        except Exception as e:
            raise e

    @override
    async def get_user_by_username(self, username: str) -> UserModel:
        try:
            result: ScalarResult[UserModel] = await self.db.exec(
                select(UserModel).where(UserModel.username == username)
            )
            user = result.one()
            if user.is_active is False:
                raise AppException(message="User account is not active")
            return user

        except NoResultFound as e:
            raise NotFoundException(
                message=f"Incorrect username or password",
            )
        except Exception as e:
            raise e

    @override
    async def get_user_by_email(self, email: EmailStr) -> UserModel:
        try:
            result: ScalarResult[UserModel] = await self.db.exec(
                select(UserModel).where(UserModel.email == email)
            )
            return result.one()

        except NoResultFound as e:
            raise NotFoundException(
                message=f"Incorrect username or password",
            )
        except Exception as e:
            raise e

    @override
    async def update_user_password(
        self, email: EmailStr, new_password: str
    ) -> UserModel:
        try:
            user: UserModel = await self.get_user_by_email(email=email)
            user.hashed_password = password_validator.get_password_hash(new_password)
            self.db.add(instance=user)
            await self.db.commit()
            await self.db.refresh(instance=user)
            return user
        except NoResultFound as e:
            raise NotFoundException(
                message=f"User with email '{email}' does not exist",
            )
        except Exception as e:
            raise e

    @override
    async def enable_2fa(self, username: str, totp_secret: str) -> UserModel:
        try:
            user: UserModel = await self.get_user_by_username(username=username)
            user.is_2fa_enabled = True
            user.totp_secret = totp_secret
            self.db.add(instance=user)
            await self.db.commit()
            await self.db.refresh(instance=user)
            return user
        except Exception as e:
            raise e
        
    @override
    async def disable_2fa(self, username: str) -> UserModel:
        try:
            user: UserModel = await self.get_user_by_username(username=username)
            user.is_2fa_enabled = False
            user.totp_secret = None
            self.db.add(instance=user)
            await self.db.commit()
            await self.db.refresh(instance=user)
            return user
        except Exception as e:
            raise e
