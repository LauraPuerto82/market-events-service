from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_state import SyncState


class SyncRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_last_synced(self, symbol: str) -> datetime | None:
        stmt = select(SyncState).where(SyncState.symbol == symbol)
        result = await self.session.execute(stmt)
        state = result.scalar_one_or_none()
        return state.last_synced_at if state else None

    async def set_last_synced(self, symbol: str, synced_at: datetime) -> None:
        stmt = (
            insert(SyncState)
            .values(symbol=symbol, last_synced_at=synced_at)
            .on_conflict_do_update(
                index_elements=["symbol"],
                set_={"last_synced_at": synced_at},
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
