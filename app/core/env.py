from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl
from typing import Literal, ClassVar
import sys


class EnvConfig(BaseSettings):
    ENV_MODE: Literal["development", "production", "test"] = "development"
    PORT: int = Field(default=3000, gt=0)  # Positive integer
    API_KEY: str = Field(default="api-secret", min_length=1)  # Required, non-empty
    SECRET_KEY: str = Field(default="secret", min_length=1)
    ALGORITHM: str = Field(default="HS256")
    VERSION: str = Field(default="1.0.0")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_WEEKS: int = Field(default=4)
    DB_URL: HttpUrl | str | None = None  # Optional URL
    DB_NAME: str | None = None  # Optional URL
    DB_PWD: str | None = None  # Optional URL
    DB_USER: str | None = None  # Optional URL
    TEST_DB_NAME: str | None = None  # Optional URL
    REDIS_URL: HttpUrl | str | None = None  # Optional URL
    REDIS_CACHE_EXPIRE: int = Field(default=300)
    FRONTEND_URL: HttpUrl | str | None = None  # Optional URL
    
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file="./.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


try:
    env: EnvConfig = EnvConfig()
except ValueError as e:
    print("❌ Invalid environment variables:", e)
    sys.exit(1)
