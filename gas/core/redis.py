from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from redis.asyncio.client import Redis

from gas.core.settings import get_settings

settings = get_settings()
_redis = Redis(
    host=settings.REDIS.HOST,
    port=settings.REDIS.PORT,
    db=settings.REDIS.DB,
    password=settings.REDIS.PASSWORD,
)


async def get_redis_session() -> AsyncGenerator[Redis]:
    async with _redis as redis:
        yield redis


redis_session = asynccontextmanager(get_redis_session)
