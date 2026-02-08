import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.app import app
from src.core.db import get_db_session
from src.modules.auth import models  # noqa: F401
from src.modules.auth.util.token import jwt_auth_token


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def test_db(tmp_path_factory):
    db_dir = tmp_path_factory.mktemp("db")
    db_path = Path(db_dir) / "auth_api_test.db"
    sync_url = f"sqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    sync_engine = create_engine(sync_url, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(sync_engine)

    async_engine = create_async_engine(async_url)
    async_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    yield {
        "sync_engine": sync_engine,
        "async_engine": async_engine,
        "async_session": async_session,
        "db_path": db_path,
    }

    async_engine.sync_engine.dispose()
    sync_engine.dispose()
    if db_path.exists():
        os.remove(db_path)


@pytest.fixture
def client(monkeypatch, test_db):
    async def _noop():
        return None

    # Use sys.modules to target the actual module object and avoid shadowing issues
    import sys

    app_module = sys.modules["src.app"]
    monkeypatch.setattr(app_module, "init_db", _noop)
    monkeypatch.setattr(app_module, "init_redis", _noop)
    monkeypatch.setattr("src.modules.auth.router.fire_and_forget", lambda *a, **k: None)

    async_session = test_db["async_session"]

    async def override_get_db_session():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sync_session(test_db):
    with Session(test_db["sync_engine"]) as session:
        yield session


@pytest.fixture
def user_factory(client, test_db):
    def _create(
        *,
        username: str,
        email: str,
        password: str,
        activate: bool = True,
    ):
        payload = {
            "username": username,
            "email": email,
            "password_one": password,
            "password_two": password,
        }
        response = client.post("/api/auth/sign-up", json=payload)
        assert response.status_code == 201

        with Session(test_db["sync_engine"]) as session:
            user = session.exec(
                select(models.UserModel).where(models.UserModel.username == username)
            ).one()

            if activate:
                token, _ = jwt_auth_token.activate_token(
                    {"username": user.username, "email": user.email, "user_id": user.id}
                )
                response = client.get(f"/api/auth/activate-account?token={token}")
                assert response.status_code == 200

            return user

    return _create


@pytest.fixture
def activated_user(client, user_factory):
    return user_factory(
        username="shared",
        email="shared@example.com",
        password="SharedCorrectHorseBatteryStaple1!",
    )


@pytest.fixture
def mfa_user(client, user_factory):
    user = user_factory(
        username="mfa_user",
        email="mfa_user@example.com",
        password="MfaCorrectHorseBatteryStaple1!",
    )

    response = client.post(
        "/api/auth/sign-in",
        json={"username": "mfa_user", "password": "MfaCorrectHorseBatteryStaple1!"},
    )
    assert response.status_code == 200
    access_token = response.json()["token"]["access_token"]["token"]

    response = client.post(
        "/api/auth/enable-2fa",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    secret = response.json()["secret"]

    return {"user": user, "secret": secret}


@pytest.fixture
def password_reset_user(client, user_factory):
    user = user_factory(
        username="reset_user",
        email="reset_user@example.com",
        password="ResetCorrectHorseBatteryStaple1!",
    )
    password_reset_token, _ = jwt_auth_token.password_reset_token(
        {"username": user.username, "email": user.email, "user_id": user.id}
    )
    return {"user": user, "password_reset_token": password_reset_token}


@pytest.fixture
def refresh_token_user(client, user_factory):
    user = user_factory(
        username="refresh_user",
        email="refresh_user@example.com",
        password="RefreshCorrectHorseBatteryStaple1!",
    )
    response = client.post(
        "/api/auth/sign-in",
        json={
            "username": "refresh_user",
            "password": "RefreshCorrectHorseBatteryStaple1!",
        },
    )
    assert response.status_code == 200
    refresh_token = response.json()["token"]["refresh_token"]["token"]
    return {"user": user, "refresh_token": refresh_token}
