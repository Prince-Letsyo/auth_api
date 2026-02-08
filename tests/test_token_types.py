import pyotp
import pytest

from src.core.exceptions import UnauthorizedException
from src.modules.auth.models import SessionModel, UserModel
from src.modules.auth.schemas.auth import PasswordResetRequest
from src.modules.auth.service import AuthService
from src.modules.auth.util.token import hash_token, jwt_auth_token


class FakeRepo:
    def __init__(self, user: UserModel) -> None:
        self.user = user
        self.sessions: dict[str, SessionModel] = {}

    async def create_user(self, user_create):
        return self.user

    async def authenticate_user(self, username: str, password: str):
        return self.user

    async def get_user_by_username(self, username: str):
        return self.user

    async def get_user_by_username_any_status(self, username: str):
        return self.user

    async def update_refresh_token_version(self, username: str, new_version: int):
        self.user.refresh_token_version = new_version
        return self.user

    async def update_totp_secret(self, username: str, totp_secret: str):
        self.user.totp_secret = totp_secret
        return self.user

    async def create_session(
        self,
        session_id: str,
        user_id: int,
        refresh_token_hash: str,
        user_agent: str | None,
        ip_address: str | None,
    ):
        session = SessionModel(
            id=session_id,
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.sessions[session_id] = session
        return session

    async def get_session(self, session_id: str):
        return self.sessions[session_id]

    async def update_session_token(self, session_id: str, refresh_token_hash: str):
        session = self.sessions[session_id]
        session.refresh_token_hash = refresh_token_hash
        self.sessions[session_id] = session
        return session

    async def revoke_session(self, session_id: str) -> None:
        session = self.sessions[session_id]
        session.revoked_at = session.revoked_at or session.created_at
        self.sessions[session_id] = session

    async def revoke_user_sessions(self, user_id: int) -> None:
        for session in self.sessions.values():
            if session.user_id == user_id:
                session.revoked_at = session.revoked_at or session.created_at

    async def list_sessions(self, user_id: int):
        return [s for s in self.sessions.values() if s.user_id == user_id]

    async def update_user_email(self, user_id: int, new_email: str):
        self.user.email = new_email
        return self.user

    async def get_user_by_email(self, email: str):
        return self.user

    async def activate_user_account(self, username: str):
        return self.user

    async def update_user_password(self, email: str, new_password: str):
        self.user.refresh_token_version += 1
        return self.user

    async def enable_2fa(self, username: str, totp_secret: str):
        return self.user

    async def disable_2fa(self, username: str):
        return self.user


def build_user() -> UserModel:
    secret = pyotp.random_base32()
    return UserModel(
        id=1,
        username="alice",
        email="alice@example.com",
        hashed_password="hashed",
        is_active=True,
        is_2fa_enabled=True,
        totp_secret=secret,
        refresh_token_version=0,
    )


def test_token_type_claims_are_set():
    payload = {"username": "alice", "email": "alice@example.com", "user_id": 1}

    access_token, _ = jwt_auth_token.access_token(payload)
    refresh_token, _ = jwt_auth_token.refresh_token(payload)
    activate_token, _ = jwt_auth_token.activate_token(payload)
    password_reset_token, _ = jwt_auth_token.password_reset_token(payload)
    temp_2fa_token, _ = jwt_auth_token.create_temp_2fa_token(payload)

    assert jwt_auth_token.decode_token(access_token)["token_type"] == "access"
    assert jwt_auth_token.decode_token(refresh_token)["token_type"] == "refresh"
    assert jwt_auth_token.decode_token(activate_token)["token_type"] == "activate"
    assert (
        jwt_auth_token.decode_token(password_reset_token)["token_type"]
        == "password_reset"
    )
    assert jwt_auth_token.decode_token(temp_2fa_token)["token_type"] == "temp_2fa"


@pytest.mark.anyio
async def test_access_token_refresh_requires_refresh_token():
    service = AuthService(FakeRepo(build_user()))
    payload = {"username": "alice", "email": "alice@example.com", "user_id": 1}
    access_token, _ = jwt_auth_token.access_token(payload)

    with pytest.raises(UnauthorizedException):
        await service.get_access_token(token_string=access_token)


@pytest.mark.anyio
async def test_activate_account_requires_activate_token():
    service = AuthService(FakeRepo(build_user()))
    payload = {"username": "alice", "email": "alice@example.com", "user_id": 1}
    refresh_token, _ = jwt_auth_token.refresh_token(payload)

    with pytest.raises(UnauthorizedException):
        await service.activate_account(token=refresh_token)


@pytest.mark.anyio
async def test_log_in_2fa_requires_temp_2fa_token():
    user = build_user()
    service = AuthService(FakeRepo(user))
    payload = {"username": user.username, "email": user.email, "user_id": user.id}
    access_token, _ = jwt_auth_token.access_token(payload)

    with pytest.raises(UnauthorizedException):
        await service.log_in_2fa(token=access_token, totp_token="123456")


@pytest.mark.anyio
async def test_password_reset_requires_password_reset_token():
    service = AuthService(FakeRepo(build_user()))
    payload = {"username": "alice", "email": "alice@example.com", "user_id": 1}
    activate_token, _ = jwt_auth_token.activate_token(payload)

    reset_request = PasswordResetRequest(
        email="alice@example.com",
        token="fake-reset-token",
        password_one="CorrectHorseBatteryStaple1!",
        password_two="CorrectHorseBatteryStaple1!",
    )

    with pytest.raises(UnauthorizedException):
        await service.password_reset(token=activate_token, rest_password=reset_request)


@pytest.mark.anyio
async def test_refresh_token_rejected_for_inactive_user():
    user = build_user()
    user.is_active = False
    service = AuthService(FakeRepo(user))
    session_id = "session-1"
    payload = {
        "username": "alice",
        "email": "alice@example.com",
        "user_id": 1,
        "sid": session_id,
    }
    refresh_token, _ = jwt_auth_token.refresh_token(payload)
    await service.repository.create_session(
        session_id=session_id,
        user_id=1,
        refresh_token_hash=hash_token(refresh_token),
        user_agent=None,
        ip_address=None,
    )

    with pytest.raises(UnauthorizedException):
        await service.get_access_token(token_string=refresh_token)


@pytest.mark.anyio
async def test_refresh_token_rejected_for_user_claim_mismatch():
    user = build_user()
    service = AuthService(FakeRepo(user))
    session_id = "session-2"
    payload = {
        "username": "alice",
        "email": "wrong@example.com",
        "user_id": 1,
        "sid": session_id,
    }
    refresh_token, _ = jwt_auth_token.refresh_token(payload)
    await service.repository.create_session(
        session_id=session_id,
        user_id=1,
        refresh_token_hash=hash_token(refresh_token),
        user_agent=None,
        ip_address=None,
    )

    with pytest.raises(UnauthorizedException):
        await service.get_access_token(token_string=refresh_token)


@pytest.mark.anyio
async def test_refresh_token_rejected_for_session_hash_mismatch():
    user = build_user()
    service = AuthService(FakeRepo(user))
    session_id = "session-3"
    payload = {
        "username": "alice",
        "email": "alice@example.com",
        "user_id": 1,
        "sid": session_id,
    }
    refresh_token, _ = jwt_auth_token.refresh_token(payload)
    await service.repository.create_session(
        session_id=session_id,
        user_id=1,
        refresh_token_hash=hash_token("different-token"),
        user_agent=None,
        ip_address=None,
    )

    with pytest.raises(UnauthorizedException):
        await service.get_access_token(token_string=refresh_token)
