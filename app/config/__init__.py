from pydantic import BaseModel
from app.core.env import EnvConfig, env
from .base import BaseConfig
from .dev import DevConfig
from .prod import ProdConfig
from .test import TestConfig

type CONFIG_TYPE = DevConfig | ProdConfig | TestConfig


class Config(BaseModel):
    app_name: str
    enable_cors: bool
    log_level: str
    database: dev.DatabaseConfig | prod.DatabaseConfig | test.DatabaseConfig
    features: dev.FeaturesConfig | prod.FeaturesConfig | test.FeaturesConfig
    redis: dev.RedisConfig | prod.RedisConfig | test.RedisConfig
    env: EnvConfig


# Environment-specific configurations
env_configs: dict[str, CONFIG_TYPE] = {
    "development": DevConfig(),
    "production": ProdConfig(),
    "test": TestConfig(),
}

# Merge base config with environment-specific config
base_config: BaseConfig = BaseConfig()
env_config: CONFIG_TYPE = env_configs[env.ENV_MODE]

config: Config = Config(
    app_name=base_config.app_name,
    enable_cors=base_config.enable_cors,
    log_level=base_config.log_level,
    database=env_config.database,
    features=env_config.features,
    redis=env_config.redis,
    env=env,
)


__all__ = ["config"]
