from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.normalizers import NormalizedEvent
from app.models.event import MarketEvent
from app.repositories.event_repository import EventRepository

# Note: this test requires a real database (integration test)
# It's here for completeness — in a real project you'd set up a test database


@pytest.mark.asyncio
async def test_upsert_creates_new_event(db_session: AsyncSession) -> None:
    """Inserting an event for the first time creates a new row"""
    repo = EventRepository(db_session)

    event = NormalizedEvent(
        symbol="AAPL",
        event_type="earnings",
        event_date=date(2026, 3, 20),
        title="AAPL Q1 2026 Earnings",
        details={"eps_estimate": 3.45},
        source="provider_a",
        source_event_id="pa-AAPL-earnings-202603",
    )

    saved, created = await repo.upsert(event)

    assert created is True
    assert saved.symbol == "AAPL"
    assert saved.event_type == "earnings"


@pytest.mark.asyncio
async def test_upsert_same_event_twice_creates_one_row(db_session: AsyncSession) -> None:
    """Upserting the same event twice results in exactly one DB row"""
    repo = EventRepository(db_session)

    event = NormalizedEvent(
        symbol="MSFT",
        event_type="dividend",
        event_date=date(2026, 6, 15),
        title="MSFT Dividend",
        details={"amount": 0.75},
        source="provider_a",
        source_event_id="pa-MSFT-div-202606",
    )

    _, created_first = await repo.upsert(event)
    _, created_second = await repo.upsert(event)

    assert created_first is True  # first time: new row
    assert created_second is False  # second time: updated existing row

    # Verify only one row exists
    count = (
        await db_session.execute(
            select(func.count())
            .select_from(MarketEvent)
            .where(
                MarketEvent.symbol == "MSFT",
                MarketEvent.event_type == "dividend",
                MarketEvent.event_date == date(2026, 6, 15),
            )
        )
    ).scalar_one()
    assert count == 1
