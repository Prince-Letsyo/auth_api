from typing import Literal
from pydantic import BaseModel

from src.core.env import env

type APP_LOG_TYPE = Literal["INFO", "WARNING", "ERROR"]


class BaseConfig(BaseModel):
    app_name: str = "Auth API"
    enable_cors: bool = True
    log_level: APP_LOG_TYPE = "INFO"
    cache_name: str = "auth-api-cache"


class DatabaseConfigMIXIN(BaseModel):
    def migrate_url(self):
        return (
            f"{env.database.driver}://{env.database.user}:{env.database.pwd}@{env.database.host}/{env.database.name}"
        )

    def session_url(self):
        return f"{env.database.driver}+psycopg://{env.database.user}:{env.database.pwd}@{env.database.host}/{env.database.name}"
