from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.event_repository import EventRepository
from app.schemas.event import EventListResponse, EventResponse
from app.services.cache_service import CacheService


class EventService:
    def __init__(self, session: AsyncSession, cache: CacheService) -> None:
        self.repo = EventRepository(session)
        self.cache = cache

    async def get_events(
        self,
        symbols: list[str] | None,
        event_type: str | None,
        from_date: date | None,
        to_date: date | None,
        limit: int,
        offset: int,
    ) -> tuple[EventListResponse, bool]:
        """Returns (response, cache_hit)"""
        cache_key = self._build_cache_key(symbols, event_type, from_date, to_date, limit, offset)

        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            return EventListResponse.model_validate_json(cached), True  # HIT

        # Cache miss - query database
        events, total = await self.repo.find_many(
            symbols=symbols, event_type=event_type, from_date=from_date, to_date=to_date, limit=limit, offset=offset
        )

        response = EventListResponse(
            data=[EventResponse.model_validate(e) for e in events],
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        )

        # Store in cache for next time
        await self.cache.set(cache_key, response.model_dump_json())

        return response, False

    def _build_cache_key(
        self,
        symbols: list[str] | None,
        event_type: str | None,
        from_date: date | None,
        to_date: date | None,
        limit: int | None,
        offset: int | None,
    ) -> str:
        parts = [
            f"symbols={','.join(sorted(symbols)) if symbols else 'all'}",
            f"type={event_type or 'all'}",
            f"from={from_date or 'none'}",
            f"to={to_date or 'none'}",
            f"limit={limit}",
            f"offset={offset}",
        ]
        return "events:" + ":".join(parts)
