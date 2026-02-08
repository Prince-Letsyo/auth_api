import pytest
from unittest.mock import MagicMock, AsyncMock
from src.modules.auth.service import AuthController
from src.core.exceptions import UnauthorizedException, AppException
from src.modules.auth.util.token import jwt_auth_token
from src.modules.auth.models import UserModel


@pytest.fixture
def auth_controller():
    repository = MagicMock()
    return AuthController(repository)


@pytest.mark.anyio
async def test_activate_account_missing_username(auth_controller, monkeypatch):
    # Mock decode_token to return payload without username
    monkeypatch.setattr(
        jwt_auth_token, "decode_token", lambda token: {"token_type": "activate"}
    )

    with pytest.raises(UnauthorizedException) as exc:
        await auth_controller.activate_account("fake_token")
    assert "missing username" in str(exc.value.message)


@pytest.mark.anyio
async def test_log_in_2fa_missing_username(auth_controller, monkeypatch):
    monkeypatch.setattr(
        jwt_auth_token,
        "decode_token",
        lambda token: {"token_type": "temp_2fa", "mfa_pending": True},
    )

    with pytest.raises(UnauthorizedException) as exc:
        await auth_controller.log_in_2fa("fake_token", "123456")
    assert "missing username" in str(exc.value.message)


@pytest.mark.anyio
async def test_log_in_2fa_missing_totp_secret(auth_controller, monkeypatch):
    monkeypatch.setattr(
        jwt_auth_token,
        "decode_token",
        lambda token: {
            "token_type": "temp_2fa",
            "mfa_pending": True,
            "username": "testuser",
        },
    )

    user = UserModel(username="testuser", is_2fa_enabled=True, totp_secret=None)
    auth_controller.repository.get_user_by_username = AsyncMock(return_value=user)

    with pytest.raises(AppException) as exc:
        await auth_controller.log_in_2fa("fake_token", "123456")
    assert "2FA secret is missing" in str(exc.value.message)


@pytest.mark.anyio
async def test_get_access_token_missing_fields(auth_controller, monkeypatch):
    monkeypatch.setattr(
        jwt_auth_token,
        "decode_token",
        lambda token: {"token_type": "refresh", "username": "user"},
    )

    with pytest.raises(UnauthorizedException) as exc:
        await auth_controller.get_access_token("fake_token")
    assert "missing required fields" in str(exc.value.message)


@pytest.mark.anyio
async def test_password_reset_missing_user_info(auth_controller, monkeypatch):
    monkeypatch.setattr(
        jwt_auth_token, "decode_token", lambda token: {"token_type": "activate"}
    )
    mock_reset_request = MagicMock()

    with pytest.raises(UnauthorizedException) as exc:
        await auth_controller.password_reset("fake_token", mock_reset_request)
    assert "missing user info" in str(exc.value.message)
