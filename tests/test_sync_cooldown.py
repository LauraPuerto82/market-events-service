from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.sync_service import SyncService


@pytest.mark.asyncio
async def test_sync_skips_recently_synced_symbol() -> None:
    """When force=False and symbol was synced < 1 hour ago, it is skipped."""

    # Create mock dependencies
    mock_session = MagicMock()
    mock_cache = AsyncMock()

    service = SyncService(mock_session, mock_cache)

    # Mock sync repo to say the symbol was synced 30 minutes ago
    recent_time = datetime.now(UTC) - timedelta(minutes=30)
    service.sync_repo = AsyncMock()
    service.sync_repo.get_last_synced = AsyncMock(return_value=recent_time)

    result = await service.sync(symbols=["AAPL"], force=False)

    assert "AAPL" in result.symbols_skipped
    assert "AAPL" not in result.symbols_synced


@pytest.mark.asyncio
async def test_sync_force_ignores_cooldown() -> None:
    """When force=True, even a recently synced symbol is synced."""

    mock_session = MagicMock()
    mock_cache = AsyncMock()

    service = SyncService(mock_session, mock_cache)

    # Mock sync_repo — symbol was synced 5 minutes ago
    recent_time = datetime.now(UTC) - timedelta(minutes=5)
    service.sync_repo = AsyncMock()
    service.sync_repo.get_last_synced = AsyncMock(return_value=recent_time)
    service.sync_repo.set_last_synced = AsyncMock()

    # Mock event_repo
    service.event_repo = AsyncMock()
    service.event_repo.upsert = AsyncMock(return_value=(MagicMock(), True))

    # Mock provider fetches
    service._fetch_provider_a = AsyncMock(return_value=[])  # type: ignore[method-assign]
    service._fetch_provider_b = AsyncMock(return_value=[])  # type: ignore[method-assign]

    result = await service.sync(symbols=["AAPL"], force=True)

    assert "AAPL" in result.symbols_synced
    assert "AAPL" not in result.symbols_skipped
