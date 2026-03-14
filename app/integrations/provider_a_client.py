import asyncio
from typing import Any, cast

from app.core.config import settings
from providers.provider_a import ProviderA, ProviderUnavailableError, RateLimitError

MAX_RETRIES = 3


async def fetch_from_provider_a(symbols: list[str]) -> list[dict[str, Any]]:
    """Fetch events from Provider A with retry logic. Returns raw provider dicts."""
    async with ProviderA(api_key=settings.provider_a_api_key) as client:
        for attempt in range(MAX_RETRIES):
            try:
                return cast(list[dict[str, Any]], await client.fetch_events(symbols))
            except RateLimitError as e:
                await asyncio.sleep(e.retry_after)
            except ProviderUnavailableError:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    raise
    return []
