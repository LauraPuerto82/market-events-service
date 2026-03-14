from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.normalizers import NormalizedEvent
from app.models.event import MarketEvent


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, event: NormalizedEvent) -> tuple[MarketEvent, bool]:
        stmt = (
            insert(MarketEvent)
            .values(
                symbol=event.symbol,
                event_type=event.event_type,
                event_date=event.event_date,
                title=event.title,
                details=event.details,
                source=event.source,
                source_event_id=event.source_event_id,
            )
            .on_conflict_do_update(
                constraint="uq_event_natural_key",
                set_={
                    "title": event.title,
                    "details": event.details,
                    "updated_at": func.now(),
                },
            )
            .returning(MarketEvent)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        saved = result.scalar_one()
        created = saved.created_at == saved.updated_at
        return saved, created

    async def find_many(
        self,
        symbols: list[str] | None = None,
        event_type: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MarketEvent], int]:
        conditions: list[Any] = []
        if symbols:
            conditions.append(MarketEvent.symbol.in_(symbols))
        if event_type:
            conditions.append(MarketEvent.event_type == event_type)
        if from_date:
            conditions.append(MarketEvent.event_date >= from_date)
        if to_date:
            conditions.append(MarketEvent.event_date <= to_date)

        where_clause = and_(*conditions) if conditions else true()

        count_stmt = select(func.count()).select_from(MarketEvent).where(where_clause)
        total = (await self.session.execute(count_stmt)).scalar_one()

        data_stmt = (
            select(MarketEvent).where(where_clause).order_by(MarketEvent.event_date.asc()).limit(limit).offset(offset)
        )
        events = (await self.session.execute(data_stmt)).scalars().all()

        return list(events), total

    async def find_by_id(self, event_id: UUID) -> MarketEvent | None:
        stmt = select(MarketEvent).where(MarketEvent.id == event_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()
