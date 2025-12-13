from pydantic import BaseModel, HttpUrl

from src.config.base import DatabaseConfigMIXIN
from src.core.env import env


class DatabaseConfig(DatabaseConfigMIXIN):
    url: HttpUrl | str | None = env.DB_URL
    logging: bool = True


class FeaturesConfig(BaseModel):
    enable_debug_routes: bool = True


class RedisConfig(BaseModel):
    url: HttpUrl | str = "redis://localhost"
    cache_expire: int = 300


class DevConfig(BaseModel):
    database: DatabaseConfig = DatabaseConfig()
    features: FeaturesConfig = FeaturesConfig()
    redis: RedisConfig = RedisConfig()
