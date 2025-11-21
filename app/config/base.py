from typing import Literal
from pydantic import BaseModel

type APP_LOG_TYPE = Literal["INFO", "WARNING", "ERROR"]


class BaseConfig(BaseModel):
    app_name: str = "Auth API"
    enable_cors: bool = True
    log_level: APP_LOG_TYPE = "INFO"
