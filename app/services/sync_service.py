import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.normalizers import normalize_provider_a, normalize_provider_b
from app.integrations.provider_a_client import fetch_from_provider_a
from app.integrations.provider_b_client import fetch_from_provider_b
from app.repositories.event_repository import EventRepository
from app.repositories.sync_repository import SyncRepository
from app.schemas.sync import SyncError, SyncResponse
from app.services.cache_service import CacheService

SYNC_COOLDOWN = timedelta(hours=1)


class SyncService:
    def __init__(self, session: AsyncSession, cache: CacheService) -> None:
        self.event_repo = EventRepository(session)
        self.sync_repo = SyncRepository(session)
        self.cache = cache

    async def sync(self, symbols: list[str], force: bool) -> SyncResponse:
        synced = []
        skipped = []
        errors = []
        created_total = 0
        updated_total = 0

        for symbol in symbols:
            # Check colddown
            if not force:
                last_synced = await self.sync_repo.get_last_synced(symbol)
                if last_synced and (datetime.now(UTC) - last_synced) < SYNC_COOLDOWN:
                    skipped.append(symbol)
                    continue

            # Fetch from both providers simultaneosly
            results = await asyncio.gather(
                self._fetch_provider_a([symbol]),
                self._fetch_provider_b([symbol]),
                return_exceptions=True,
            )

            provider_a_result, provider_b_result = results
            all_normalized = []

            if isinstance(provider_a_result, BaseException):
                errors.append(SyncError(symbol=symbol, provider="provider_a", error=str(provider_a_result)))
            else:
                for raw in provider_a_result:
                    all_normalized.append(normalize_provider_a(raw))

            if isinstance(provider_b_result, BaseException):
                errors.append(SyncError(symbol=symbol, provider="provider_b", error=str(provider_b_result)))
            else:
                for raw in provider_b_result:
                    all_normalized.append(normalize_provider_b(raw))

            for event in all_normalized:
                _, was_created = await self.event_repo.upsert(event)
                if was_created:
                    created_total += 1
                else:
                    updated_total += 1

            await self.sync_repo.set_last_synced(symbol, datetime.now(UTC))
            synced.append(symbol)

            await self.cache.invalidate_prefix("events:")

        return SyncResponse(
            status="completed",
            symbols_synced=synced,
            symbols_skipped=skipped,
            events_created=created_total,
            events_updated=updated_total,
            errors=errors,
        )

    async def _fetch_provider_a(self, symbols: list[str]) -> list[dict[str, Any]]:
        return await fetch_from_provider_a(symbols)

    async def _fetch_provider_b(self, symbols: list[str]) -> list[dict[str, Any]]:
        return await fetch_from_provider_b(symbols)
