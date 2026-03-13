from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class EventResponse(BaseModel):
    id: UUID
    symbol: str
    event_type: str
    event_date: date
    title: str
    details: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    data: list[EventResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
