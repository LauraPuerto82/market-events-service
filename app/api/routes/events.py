from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.repositories.event_repository import EventRepository
from app.schemas.event import EventListResponse, EventResponse
from app.schemas.sync import SyncRequest, SyncResponse
from app.services.cache_service import CacheService
from app.services.event_service import EventService
from app.services.sync_service import SyncService

router = APIRouter(prefix="/api/v1", tags=["events"])


def get_cache(request: Request) -> CacheService:
    return CacheService(request.app.state.redis)


@router.get("/events", response_model=EventListResponse)
async def list_events(
    response: Response,
    symbols: str | None = Query(None, description="Comma-separated symbols"),
    event_type: str | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache),
) -> EventListResponse:
    symbol_list = [s.strip().upper() for s in symbols.split(",")] if symbols else None
    service = EventService(db, cache)
    result, cache_hit = await service.get_events(
        symbols=symbol_list, event_type=event_type, from_date=from_date, to_date=to_date, limit=limit, offset=offset
    )
    response.headers["X-Cache"] = "HIT" if cache_hit else "MISS"
    return result


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    repo = EventRepository(db)
    event = await repo.find_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse.model_validate(event)


@router.post("/events/sync", response_model=SyncResponse)
async def sync_events(
    body: SyncRequest,
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache),
) -> SyncResponse:
    service = SyncService(db, cache)
    return await service.sync(body.symbols, body.force)
