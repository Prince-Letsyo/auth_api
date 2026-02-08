from typing import cast
import pytest
from fastapi import Request
from src.middlewares.request import redact_headers, filter_sensitive, get_current_user
from src.modules.auth.models import SessionModel, UserModel
from src.core.exceptions import UnauthorizedException


def test_redact_headers():
    headers = {
        "Authorization": "Bearer secret",
        "Content-Type": "application/json",
        "Cookie": "session=123",
        "X-API-Key": "key",
    }
    redacted = redact_headers(headers)
    assert redacted["Authorization"] == "[REDACTED]"
    assert redacted["Cookie"] == "[REDACTED]"
    assert redacted["X-API-Key"] == "[REDACTED]"
    assert redacted["Content-Type"] == "application/json"


def test_filter_sensitive_dict():
    data = {"password": "secret", "username": "user", "token": "secret_token"}
    filtered = filter_sensitive(data)
    assert isinstance(filtered, dict)
    assert filtered["password"] == "***"
    assert filtered["username"] == "user"
    assert filtered["token"] == "[REDACTED]"


def test_filter_sensitive_str():
    data = "simple string"
    filtered = filter_sensitive(data)
    assert filtered == "simple string"


@pytest.mark.anyio
async def test_get_current_user_success():
    payload = {"sub": "user_id", "username": "user", "exp": 123, "sid": "s1", "user_id": 1}

    class MockState:
        user = payload

    class MockRequest:
        state = MockState()

    class _Result:
        def __init__(self, value):
            self._value = value

        def one(self):
            return self._value

    class _FakeSession:
        def __init__(self):
            self._calls = 0

        async def exec(self, _stmt):
            self._calls += 1
            if self._calls == 1:
                return _Result(SessionModel(id="s1", user_id=1, refresh_token_hash="x"))
            return _Result(
                UserModel(
                    id=1,
                    username="user",
                    email="user@example.com",
                    hashed_password="x",
                    is_active=True,
                )
            )

    user = await get_current_user(cast(Request, MockRequest()), session=_FakeSession())
    assert user == payload


@pytest.mark.anyio
async def test_get_current_user_unauthorized():
    class MockState:
        user = None

    class MockRequest:
        state = MockState()

    with pytest.raises(UnauthorizedException) as exc:
        await get_current_user(cast(Request, MockRequest()))
    assert exc.value.status_code == 401
