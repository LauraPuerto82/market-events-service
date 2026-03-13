from pydantic import BaseModel


class SyncRequest(BaseModel):
    symbols: list[str]
    force: bool = False


class SyncError(BaseModel):
    symbol: str
    provider: str
    error: str


class SyncResponse(BaseModel):
    status: str
    symbols_synced: list[str]
    symbols_skipped: list[str]
    events_created: int
    events_updated: int
    errors: list[SyncError]
