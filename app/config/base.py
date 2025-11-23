from typing import Literal
from pydantic import BaseModel

from app.core.env import env

type APP_LOG_TYPE = Literal["INFO", "WARNING", "ERROR"]


class BaseConfig(BaseModel):
    app_name: str = "Auth API"
    enable_cors: bool = True
    log_level: APP_LOG_TYPE = "INFO"
    cache_name: str = "auth-api-cache"


class DatabaseConfigMIXIN(BaseModel):
    def migrate_url(self):
        return (
            f"{env.DB_DRIVER}://{env.DB_USER}:{env.DB_PWD}@{env.DB_HOST}/{env.DB_NAME}"
        )

    def session_url(self):
        return f"{env.DB_DRIVER}+psycopg://{env.DB_USER}:{env.DB_PWD}@{env.DB_HOST}/{env.DB_NAME}"
