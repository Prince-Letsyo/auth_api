from pydantic import BaseModel, HttpUrl
from src.config.base import DatabaseConfigMIXIN
from src.core.env import env


class DatabaseConfig(DatabaseConfigMIXIN):
    url: HttpUrl | str | None = env.DB_URL  # Use validated env variable
    logging: bool = False


class FeaturesConfig(BaseModel):
    enable_debug_routes: bool = False


class RedisConfig(BaseModel):
    url: HttpUrl | str | None = env.REDIS_URL  # Use validated env variable
    cache_expire: int | None = env.REDIS_CACHE_EXPIRE


class ProdConfig(BaseModel):
    database: DatabaseConfig = DatabaseConfig()
    features: FeaturesConfig = FeaturesConfig()
    redis: RedisConfig = RedisConfig()
