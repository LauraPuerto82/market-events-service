from typing import cast

import redis.asyncio as aioredis

from app.core.config import settings


class CacheService:
    def __init__(self, client: aioredis.Redis) -> None:
        self.client = client

    async def get(self, key: str) -> str | None:
        return cast(str | None, await self.client.get(key))

    async def set(self, key: str, value: str) -> None:
        await self.client.setex(key, settings.cache_ttl_seconds, value)

    async def invalidate_prefix(self, prefix: str) -> None:
        """Delete all keys starting with the given prefix."""
        keys = await self.client.keys(f"{prefix}*")
        if keys:
            await self.client.delete(*keys)
