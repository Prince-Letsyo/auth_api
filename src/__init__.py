from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from typing import Any

from src.api import register_api_routes
from src.config import config
from src.core.db import init_db
from src.core.redis import init_redis
from src.utils.logging import main_logger
from src.core.exception import AppException
from src.middlewares.exception import (
    app_exception_handler,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from src.middlewares.request import (
    jwt_decoder,
    logging_middleware,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    main_logger.info("🚀 Starting database migration...")
    try:
        await init_db()
        main_logger.info("✅ Database migration completed!")
        await init_redis()
        main_logger.info("✅ Redis cache initialized successfully.")
    except ConnectionError as e:
        main_logger.error(f"❌ Redis connection failed: {e}")
        raise e
    except Exception as e:
        main_logger.error(f"❌ Migration failed: {e}")
        raise e
    yield


app = FastAPI(
    title=config.app_name,
    license_info={"name": "MIT License"},
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


def custom_openapi() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema: dict[str, Any] = get_openapi(  # pyright: ignore[reportExplicitAny]
        title=config.app_name,
        version=config.env.VERSION,
        description="A simple Task Management API built with FastAPI",
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
    for path in openapi_schema["paths"].values():  # pyright: ignore[reportAny]
        for method in path.values():  # pyright: ignore[reportAny]
            method.setdefault(  # pyright: ignore[reportAny]
                "security", [{"BearerAuth": []}]
            )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.add_exception_handler(
    exc_class_or_status_code=RequestValidationError,
    handler=validation_exception_handler,  # pyright: ignore[reportArgumentType]
)

app.add_exception_handler(
    exc_class_or_status_code=HTTPException,
    handler=http_exception_handler,  # pyright: ignore[reportArgumentType]
)
app.add_exception_handler(
    exc_class_or_status_code=AppException,
    handler=app_exception_handler,  # pyright: ignore[reportArgumentType]
)
app.add_exception_handler(
    exc_class_or_status_code=Exception, handler=global_exception_handler
)

if config.enable_cors:
    app.add_middleware(
        middleware_class=CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
_ = app.middleware(middleware_type="http")(jwt_decoder)
_ = app.middleware(middleware_type="http")(logging_middleware)


register_api_routes(app)

@app.get("/")
def index():
    return {"message": "Welcome to Authentication Api Project!"}




