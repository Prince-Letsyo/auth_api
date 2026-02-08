import pytest
from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from src.middlewares.exception import (
    http_exception_handler,
    validation_exception_handler,
    app_exception_handler,
    global_exception_handler,
)
from src.core.exceptions import AppException


@pytest.mark.anyio
async def test_http_exception_handler():
    exc = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    response = await http_exception_handler(None, exc)
    assert response.status_code == 404
    body = response.body.decode()
    assert '"success":false' in body.lower()
    assert '"message":"not found"' in body.lower()


@pytest.mark.anyio
async def test_validation_exception_handler():
    # Mocking a simple validation error structure
    errors = [{"loc": ("body", "email"), "msg": "invalid email", "type": "value_error"}]
    exc = RequestValidationError(errors=errors)
    response = await validation_exception_handler(None, exc)
    assert response.status_code == 422
    body = response.body.decode()
    assert '"success":false' in body.lower()
    assert '"field":"email"' in body.lower()
    assert '"message":"invalid email"' in body.lower()


@pytest.mark.anyio
async def test_app_exception_handler():
    exc = AppException(message="Custom Error", status_code=400)
    response = await app_exception_handler(None, exc)
    assert response.status_code == 400
    body = response.body.decode()
    assert '"success":false' in body.lower()
    assert '"error":"custom error"' in body.lower()


@pytest.mark.anyio
async def test_global_exception_handler():
    exc = Exception("Unexpected Error")
    response = await global_exception_handler(None, exc)
    assert response.status_code == 500
    body = response.body.decode()
    assert '"success":false' in body.lower()
    assert "internal server error" in body.lower()
