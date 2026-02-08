import pytest
from fastapi import Request
from fastapi.responses import Response

from src.modules.auth.util.token import jwt_auth_token
from src.middlewares.request import jwt_decoder


@pytest.mark.anyio
async def test_jwt_decoder_rejects_non_access_token():
    payload = {"username": "alice", "email": "alice@example.com", "user_id": 1}
    refresh_token, _ = jwt_auth_token.refresh_token(payload)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"authorization", f"Bearer {refresh_token}".encode("utf-8"))],
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)

    async def call_next(_request: Request):
        return Response("ok")

    response = await jwt_decoder(request, call_next)
    assert response.status_code == 401


@pytest.mark.anyio
async def test_jwt_decoder_accepts_access_token():
    payload = {"username": "alice", "email": "alice@example.com", "user_id": 1}
    access_token, _ = jwt_auth_token.access_token(payload)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"authorization", f"Bearer {access_token}".encode("utf-8"))],
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)

    async def call_next(_request: Request):
        return Response("ok")

    response = await jwt_decoder(request, call_next)
    assert response.status_code == 200
    assert request.state.user["username"] == "alice"
