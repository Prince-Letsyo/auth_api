import json
from typing import cast

from fastapi_cache import FastAPICache, JsonCoder
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import Redis
from redis.exceptions import ConnectionError

from src.config import config


class SafeJsonCoder(JsonCoder):
    @classmethod
    def decode(  # pyright: ignore[reportAny, reportImplicitOverride]
        cls, value  # pyright: ignore[reportMissingParameterType]
    ):
        if isinstance(value, bytes):  # pyright: ignore[reportUnnecessaryIsInstance]
            value = value.decode("utf-8")  # decode bytes to str
        # If it's already str, just pass it directly to json.loads
        return json.loads(value)  # pyright: ignore[reportAny]


async def init_redis() -> None:
    try:
        _redis: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
            url=cast(str, config.redis.url),
            encoding="utf8",
            decode_responses=True,
        )
        await _redis.ping()  # pyright: ignore[reportUnknownMemberType, reportUnusedCallResult, reportGeneralTypeIssues]
        FastAPICache.init(
            coder=SafeJsonCoder,
            backend=RedisBackend(redis=_redis),
            prefix=config.cache_name,
            expire=cast(int, config.redis.cache_expire),
        )
    except ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        raise RuntimeError("Failed to initialize Redis cache") from e
