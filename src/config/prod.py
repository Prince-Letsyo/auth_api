from pydantic import BaseModel, HttpUrl

from src.config.base import DatabaseConfigMIXIN
from src.core.env import env


class DatabaseConfig(DatabaseConfigMIXIN):
    url: HttpUrl | str | None = env.database.url
    logging: bool = False


class FeaturesConfig(BaseModel):
    enable_debug_routes: bool = False


class RedisConfig(BaseModel):
    url: HttpUrl | str | None = env.redis.url
    cache_expire: int | None = env.redis.cache_expire


class ProdConfig(BaseModel):
    database: DatabaseConfig = DatabaseConfig()
    features: FeaturesConfig = FeaturesConfig()
    redis: RedisConfig = RedisConfig()
