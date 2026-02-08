from typing import override

from pydantic import EmailStr
from sqlalchemy import ScalarResult, update
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.modules.auth.repositories.base import BaseAuthRepository
from src.modules.auth.schemas.auth import UserCreate
from src.modules.auth.util.password import password_validator
from src.core.exceptions import AppException, ConflictException, NotFoundException
from src.modules.auth.models import SessionModel, UserModel


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
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException(
                message="User already exist",
            )
        except Exception as e:
            await self.db.rollback()
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
        except NoResultFound:
            raise NotFoundException(
                message=f"User with username '{username}' does not exist",
            )
        except Exception as e:
            await self.db.rollback()
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
                raise AppException(message="Incorrect username or password")
            return user

        except NoResultFound:
            raise NotFoundException(
                message="Incorrect username or password",
            )
        except Exception as e:
            raise e

    @override
    async def get_user_by_username_any_status(self, username: str) -> UserModel:
        try:
            result: ScalarResult[UserModel] = await self.db.exec(
                select(UserModel).where(UserModel.username == username)
            )
            return result.one()
        except NoResultFound:
            raise NotFoundException(
                message="Incorrect username or password",
            )
        except Exception as e:
            raise e

    @override
    async def update_refresh_token_version(
        self, username: str, new_version: int
    ) -> UserModel:
        try:
            user: UserModel = await self.get_user_by_username_any_status(username)
            user.refresh_token_version = new_version
            self.db.add(instance=user)
            await self.db.commit()
            await self.db.refresh(instance=user)
            return user
        except Exception as e:
            await self.db.rollback()
            raise e

    @override
    async def update_totp_secret(self, username: str, totp_secret: str) -> UserModel:
        try:
            user: UserModel = await self.get_user_by_username_any_status(username)
            user.totp_secret = totp_secret
            self.db.add(instance=user)
            await self.db.commit()
            await self.db.refresh(instance=user)
            return user
        except Exception as e:
            await self.db.rollback()
            raise e

    @override
    async def get_user_by_email(self, email: EmailStr) -> UserModel:
        try:
            result: ScalarResult[UserModel] = await self.db.exec(
                select(UserModel).where(UserModel.email == email)
            )
            return result.one()

        except NoResultFound:
            raise NotFoundException(
                message="Incorrect username or password",
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
        except NoResultFound:
            raise NotFoundException(
                message=f"User with email '{email}' does not exist",
            )
        except Exception as e:
            await self.db.rollback()
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
            await self.db.rollback()
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
            await self.db.rollback()
            raise e

    @override
    async def create_session(
        self,
        session_id: str,
        user_id: int,
        refresh_token_hash: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> SessionModel:
        try:
            session = SessionModel(
                id=session_id,
                user_id=user_id,
                refresh_token_hash=refresh_token_hash,
                user_agent=user_agent,
                ip_address=ip_address,
            )
            self.db.add(instance=session)
            await self.db.commit()
            await self.db.refresh(instance=session)
            return session
        except Exception as e:
            await self.db.rollback()
            raise e

    @override
    async def get_session(self, session_id: str) -> SessionModel:
        try:
            result: ScalarResult[SessionModel] = await self.db.exec(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            return result.one()
        except NoResultFound:
            raise NotFoundException(message="Session not found")
        except Exception as e:
            raise e

    @override
    async def update_session_token(
        self, session_id: str, refresh_token_hash: str
    ) -> SessionModel:
        try:
            session = await self.get_session(session_id=session_id)
            session.refresh_token_hash = refresh_token_hash
            session.last_used_at = func.now()
            self.db.add(instance=session)
            await self.db.commit()
            await self.db.refresh(instance=session)
            return session
        except Exception as e:
            await self.db.rollback()
            raise e

    @override
    async def revoke_session(self, session_id: str) -> None:
        try:
            session = await self.get_session(session_id=session_id)
            session.revoked_at = func.now()
            self.db.add(instance=session)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise e

    @override
    async def revoke_user_sessions(self, user_id: int) -> None:
        try:
            await self.db.exec(
                update(SessionModel)
                .where(SessionModel.user_id == user_id)
                .values(revoked_at=func.now())
            )
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise e

    @override
    async def list_sessions(self, user_id: int) -> list[SessionModel]:
        try:
            result: ScalarResult[SessionModel] = await self.db.exec(
                select(SessionModel)
                .where(SessionModel.user_id == user_id)
                .order_by(SessionModel.created_at.desc())
            )
            return list(result.all())
        except Exception as e:
            raise e

    @override
    async def update_user_email(self, user_id: int, new_email: EmailStr) -> UserModel:
        try:
            result: ScalarResult[UserModel] = await self.db.exec(
                select(UserModel).where(UserModel.id == user_id)
            )
            user = result.one()
            user.email = new_email
            self.db.add(instance=user)
            await self.db.commit()
            await self.db.refresh(instance=user)
            return user
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException(message="Email already in use")
        except Exception as e:
            await self.db.rollback()
            raise e
