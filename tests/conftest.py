from collections.abc import AsyncGenerator
from datetime import date

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.event import MarketEvent

test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)

# Natural keys used in deduplication tests — cleaned up before each test
_TEST_EVENT_DATES = [date(2026, 3, 20), date(2026, 6, 15)]


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as cleanup:
        await cleanup.execute(
            delete(MarketEvent).where(MarketEvent.event_date.in_(_TEST_EVENT_DATES))
        )
        await cleanup.commit()

    async with TestSessionLocal() as session:
        yield session
