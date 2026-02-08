from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from src.api import register_api_routes
from src.config import config
from src.core.db import init_db
from src.core.exceptions import AppException
from src.core.redis import init_redis
from src.core.openapi import custom_openapi
from src.middlewares.exception import (
    app_exception_handler,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from src.middlewares.request import jwt_decoder, logging_middleware
from src.core.logging import main_logger


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    main_logger.info("🚀 Starting database migration...")
    try:
        await init_db()
        main_logger.info("✅ Database migration completed!")
        await init_redis()
        main_logger.info("✅ Redis cache initialized successfully.")
    except ConnectionError as e:
        main_logger.info(f"❌ Redis connection failed: {e}")
        raise e
    except Exception as e:
        main_logger.info(f"❌ Migration failed: {e}")
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


app.openapi = lambda: custom_openapi(app)

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
    frontend_url = config.env.frontend_url
    if frontend_url:
        allow_origins = [str(frontend_url)]
        allow_credentials = True
    else:
        allow_origins = ["*"]
        allow_credentials = False
    app.add_middleware(
        middleware_class=CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
_ = app.middleware(middleware_type="http")(jwt_decoder)
_ = app.middleware(middleware_type="http")(logging_middleware)


register_api_routes(app)


@app.get("/")
def index():
    return {"message": "Welcome to Authentication Api Project!"}
