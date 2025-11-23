from typing import override
from pydantic import BaseModel, HttpUrl

from app.config.base import DatabaseConfigMIXIN


class DatabaseConfig(DatabaseConfigMIXIN):
    url: HttpUrl | str = "sqlite+aiosqlite:///./test.db"
    logging: bool = False

    @override
    def session_url(self):
        return "sqlite+aiosqlite:///./test.db"

    @override
    def migrate_url(self):
        return f"sqlite:///./test.db"


class FeaturesConfig(BaseModel):
    enable_debug_routes: bool = False


class RedisConfig(BaseModel):
    url: HttpUrl | str | None = None
    cache_expire: int = 300


class TestConfig(BaseModel):
    database: DatabaseConfig = DatabaseConfig()
    features: FeaturesConfig = FeaturesConfig()
    redis: RedisConfig = RedisConfig()
