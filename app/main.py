from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI

from app.api.routes import events, health
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # On startup: create Redis client
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
    yield
    # On shutdown: close Redis connection
    await app.state.redis.aclose()


app = FastAPI(title="Market Events Service", version="0.1.0", lifespan=lifespan)
app.include_router(events.router)
app.include_router(health.router)
