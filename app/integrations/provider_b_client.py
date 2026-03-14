import asyncio
from typing import Any

from app.core.config import settings
from providers.provider_b import ProviderB, ProviderTimeoutError, RateLimitError

MAX_RETRIES = 2
MAX_PAGES = 50
RETRY_TIME = 2.0


async def fetch_from_provider_b(symbols: list[str]) -> list[dict[str, Any]]:
    """Fetch ALL pages of events from Provider B. Handles pagination and stuck-page detection"""
    all_events = []

    async with ProviderB(api_key=settings.provider_b_api_key) as client:
        cursor = None
        seen_event_ids: set[str] = set()
        pages_fetched = 0

        while pages_fetched < MAX_PAGES:
            result = await _fetch_page_with_retry(client, symbols, cursor)
            if result is None:
                break

            events = result["events"]
            pagination = result["pagination"]

            # Stuck pagination detection
            page_ids = {e["id"] for e in events}
            if page_ids and page_ids.issubset(seen_event_ids):
                break

            seen_event_ids.update(page_ids)
            all_events.extend(events)
            pages_fetched += 1

            if not pagination["has_next"]:
                break

            cursor = pagination["next_cursor"]

    return all_events


async def _fetch_page_with_retry(client: ProviderB, symbols: list[str], cursor: str | None) -> dict[str, Any] | None:
    """Fetch one page, retrying on timeout"""
    for attempt in range(MAX_RETRIES):
        try:
            return await client.fetch_events(symbols, cursor=cursor)
        except RateLimitError as e:
            await asyncio.sleep(e.retry_after)
        except ProviderTimeoutError:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_TIME)
            else:
                return None
    return None
