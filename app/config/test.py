from pydantic import BaseModel, HttpUrl


class DatabaseConfig(BaseModel):
    url: HttpUrl | str = "sqlite+aiosqlite:///./test.db"
    logging: bool = False


class FeaturesConfig(BaseModel):
    enable_debug_routes: bool = False


class RedisConfig(BaseModel):
    url: HttpUrl | str | None = None
    cache_expire: int = 300


class TestConfig(BaseModel):
    database: DatabaseConfig = DatabaseConfig()
    features: FeaturesConfig = FeaturesConfig()
    redis: RedisConfig = RedisConfig()
