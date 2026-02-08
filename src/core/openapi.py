from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from src.config import config
from src.middlewares.request import get_current_user


def _route_requires_auth(route: APIRoute) -> bool:
    for dependency in route.dependant.dependencies:
        if dependency.call is get_current_user:
            return True
    return False


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=config.app_name,
        version=config.env.version,
        description="A simple Authentication API built with FastAPI",
        contact={"name": "Prince Kumar", "email": "test@gm.com"},
        routes=app.routes,
    )

    # Add JWT Bearer auth definition
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token in the format: Bearer <token>",
        }
    }

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not _route_requires_auth(route):
            continue

        path_item = openapi_schema["paths"].get(route.path, {})
        for method in route.methods or []:
            method_item = path_item.get(method.lower())
            if method_item is None:
                continue
            method_item.setdefault("security", [{"BearerAuth": []}])

    app.openapi_schema = openapi_schema
    return app.openapi_schema
