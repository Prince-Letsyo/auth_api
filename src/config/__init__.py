from pydantic import BaseModel
from src.core.env import EnvConfig, env
from .base import BaseConfig
from .dev import DevConfig
from .prod import ProdConfig
from .test import TestConfig

type CONFIG_TYPE = DevConfig | ProdConfig | TestConfig
type DATABASE_CONFIG_TYPE = dev.DatabaseConfig | prod.DatabaseConfig | test.DatabaseConfig
type FEATURES_CONFIG_TYPE = dev.FeaturesConfig | prod.FeaturesConfig | test.FeaturesConfig
type REDIS_CONFIG_TYPE = dev.RedisConfig | prod.RedisConfig | test.RedisConfig


class Config(BaseModel):
    app_name: str
    enable_cors: bool
    log_level: str
    cache_name:str
    database: DATABASE_CONFIG_TYPE
    features: FEATURES_CONFIG_TYPE
    redis: REDIS_CONFIG_TYPE
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
    cache_name=base_config.cache_name,
    log_level=base_config.log_level,
    database=env_config.database,
    features=env_config.features,
    redis=env_config.redis,
    env=env,
)


__all__ = ["config"]
