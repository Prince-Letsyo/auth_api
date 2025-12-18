import sys
from typing import Literal, override

from pydantic import BaseModel, EmailStr, Field, HttpUrl
from pydantic_settings import (BaseSettings, SettingsConfigDict,
                               YamlConfigSettingsSource)
from pydantic_settings.sources import PydanticBaseSettingsSource


class DatabaseConfig(BaseModel):
    url: HttpUrl | str | None = None
    host: HttpUrl | str | None = None
    name: str | None = None
    pwd: str | None = None
    user: str | None = None
    driver: str | None = None
    test_name: str | None = None


class TokenConfig(BaseModel):
    secret_key: str = Field(default="", min_length=1)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_weeks: int = 4
    temp_2fa_token_expire_minutes: int = 5


class RedisConfig(BaseModel):
    url: HttpUrl | str | None = None
    cache_expire: int = 300


class SmtpServerConfig(BaseModel):
    username: str = ""
    password: str = ""
    from_email: EmailStr = Field(default="no-reply@example.com", min_length=5)
    hostname: str = Field(default="localhost", min_length=1)
    port: int = Field(default=25, gt=0)
    use_tls: bool = Field(default=False)
    use_ssl: bool = Field(default=False)
    credentials: bool = Field(default=False)
    validate_certs: bool = Field(default=True)
    server: str = Field(default="127.0.0.1", min_length=1)

class EnvConfig(BaseSettings):
    app: str = "src:app"
    host: str = "127.0.01"
    reload: bool = True
    log_level: str = "info"
    env_mode: Literal["development", "production", "test"] = "development"
    port: int = Field(default=3000, gt=0)
    api_key: str = Field(default="", min_length=1)
    version: str = "1.0.0"
    redis: RedisConfig = RedisConfig()
    token: TokenConfig = TokenConfig()
    database: DatabaseConfig = DatabaseConfig()
    smtp_server: SmtpServerConfig = SmtpServerConfig()
    celery_broker_url: HttpUrl | str | None = None
    frontend_url: HttpUrl | str | None = None

    model_config = (  # pyright: ignore[reportUnannotatedClassAttribute]
        SettingsConfigDict(
            yaml_file="config.yaml",
            yaml_file_encoding="utf-8",
            case_sensitive=False,
        )
    )

    @override
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,  # pyright: ignore[reportMissingParameterType]
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            YamlConfigSettingsSource(settings_cls),
            env_settings,  # Optional: keep if you want env vars to override YAML
        )


try:
    env: EnvConfig = EnvConfig()
except ValueError as e:
    print("❌ Invalid environment variables:", e)
    sys.exit(1)
