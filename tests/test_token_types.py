import pyotp
import pytest

from src.core.exceptions import UnauthorizedException
from src.modules.auth.models import UserModel
from src.modules.auth.schemas.auth import PasswordResetRequest
from src.modules.auth.service import AuthController
from src.modules.auth.util.token import jwt_auth_token


class FakeRepo:
    def __init__(self, user: UserModel) -> None:
        self.user = user

    async def create_user(self, user_create):
        return self.user

    async def authenticate_user(self, username: str, password: str):
        return self.user

    async def get_user_by_username(self, username: str):
        return self.user

    async def get_user_by_email(self, email: str):
        return self.user

    async def activate_user_account(self, username: str):
        return self.user

    async def update_user_password(self, email: str, new_password: str):
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
    )


def test_token_type_claims_are_set():
    payload = {"username": "alice", "email": "alice@example.com", "user_id": 1}

    access_token, _ = jwt_auth_token.access_token(payload)
    refresh_token, _ = jwt_auth_token.refresh_token(payload)
    activate_token, _ = jwt_auth_token.activate_token(payload)
    temp_2fa_token, _ = jwt_auth_token.create_temp_2fa_token(payload)

    assert jwt_auth_token.decode_token(access_token)["token_type"] == "access"
    assert jwt_auth_token.decode_token(refresh_token)["token_type"] == "refresh"
    assert jwt_auth_token.decode_token(activate_token)["token_type"] == "activate"
    assert jwt_auth_token.decode_token(temp_2fa_token)["token_type"] == "temp_2fa"


@pytest.mark.anyio
async def test_access_token_refresh_requires_refresh_token():
    controller = AuthController(FakeRepo(build_user()))
    payload = {"username": "alice", "email": "alice@example.com", "user_id": 1}
    access_token, _ = jwt_auth_token.access_token(payload)

    with pytest.raises(UnauthorizedException):
        await controller.get_access_token(token_string=access_token)


@pytest.mark.anyio
async def test_activate_account_requires_activate_token():
    controller = AuthController(FakeRepo(build_user()))
    payload = {"username": "alice", "email": "alice@example.com", "user_id": 1}
    refresh_token, _ = jwt_auth_token.refresh_token(payload)

    with pytest.raises(UnauthorizedException):
        await controller.activate_account(token=refresh_token)


@pytest.mark.anyio
async def test_log_in_2fa_requires_temp_2fa_token():
    user = build_user()
    controller = AuthController(FakeRepo(user))
    payload = {"username": user.username, "email": user.email, "user_id": user.id}
    access_token, _ = jwt_auth_token.access_token(payload)

    with pytest.raises(UnauthorizedException):
        await controller.log_in_2fa(token=access_token, totp_token="123456")


@pytest.mark.anyio
async def test_password_reset_requires_activate_token():
    controller = AuthController(FakeRepo(build_user()))
    payload = {"username": "alice", "email": "alice@example.com", "user_id": 1}
    refresh_token, _ = jwt_auth_token.refresh_token(payload)

    reset_request = PasswordResetRequest(
        email="alice@example.com",
        password_one="CorrectHorseBatteryStaple1!",
        password_two="CorrectHorseBatteryStaple1!",
    )

    with pytest.raises(UnauthorizedException):
        await controller.password_reset(
            token=refresh_token, rest_password=reset_request
        )
