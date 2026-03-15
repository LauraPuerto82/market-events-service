from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.database.session import get_db
from app.main import app


def _make_mock_session() -> AsyncMock:
    """Mock session that handles find_many's two execute calls (COUNT then SELECT)."""
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[count_result, rows_result])
    return mock_session


@pytest.fixture(autouse=True)
def mock_dependencies() -> Generator[None, None, None]:
    app.state.redis = AsyncMock()
    app.state.redis.get = AsyncMock(return_value=None)
    app.state.redis.set = AsyncMock()
    app.state.redis.ping = AsyncMock()
    app.state.redis.keys = AsyncMock(return_value=[])
    app.state.redis.delete = AsyncMock()

    async def mock_get_db() -> AsyncGenerator[AsyncMock, None]:
        yield _make_mock_session()

    app.dependency_overrides[get_db] = mock_get_db
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_returns_ok() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_list_events_returns_paginated_response() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/events")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert "has_more" in data


@pytest.mark.asyncio
async def test_list_events_limit_validation() -> None:
    """limit > 500 should fail validation"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/events?limit=999")
    assert response.status_code == 422  # validation error


@pytest.mark.asyncio
async def test_get_event_invalid_uuid() -> None:
    """A non-UUID string in the path returns 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/events/not-a-valid-uuid")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sync_requires_symbols() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/events/sync", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_cache_header_present() -> None:
    """X-Cache header is present in events response."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/events")
    assert "x-cache" in response.headers
    assert response.headers["x-cache"] in ("HIT", "MISS")
