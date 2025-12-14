import json
import re
from re import Pattern
from typing import Any
from loguru import logger
from loguru._handler import Message
from src.config import config


def app_logger():
    """
    Configure Loguru logger with file sink, rotation, and sensitive data filter.
    """
    _ = logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="7 days",
        level=(
            "DEBUG" if config.env.env_mode in {"development", "test"} else "INFO"
        ),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {extra} | {message}",
        enqueue=True,
        compression="zip",
    )

    # Add JSON sink for structured logging
    def json_sink(message: Message) -> None:
        record = message.record
        log_entry: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
            "time": record["time"].strftime("%Y-%m-%d %H:%M:%S"),
            "level": record["level"].name,
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
            "extra": record["extra"],
        }
        with open("logs/json.log", "a") as f:
            _ = f.write(json.dumps(log_entry) + "\n")

    logger.add(json_sink, format="{message}")  # pyright: ignore[reportCallIssue, reportArgumentType]
    return logger


# Regex patterns
PASSWORD_PATTERN: Pattern[str] = re.compile(r"\b([Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd][_][Oo][Nn][Ee]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd][_][Tt][Ww][Oo])\b", re.IGNORECASE)
TOKEN_PATTERN: Pattern[str] = re.compile(r"\b(token|api_key|secret|auth)\b", re.IGNORECASE)


def filter_sensitive(data: dict[str, str | int] | str):
    if isinstance(data, dict):
        for key in data:
            if PASSWORD_PATTERN.search(key):
                data[key] = "***"
            elif TOKEN_PATTERN.search(key):
                data[key] = "[REDACTED]"
    return data


main_logger = app_logger()
