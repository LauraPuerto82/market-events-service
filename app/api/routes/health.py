from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database.session import AsyncSessionLocal

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health(request: Request) -> JSONResponse:
    db_status = "ok"
    cache_status = "ok"

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        await request.app.state.redis.ping()
    except Exception:
        cache_status = "error"

    overall = "ok" if db_status == "ok" and cache_status == "ok" else "error"
    status_code = 200 if overall == "ok" else 503

    return JSONResponse(
        status_code=status_code, content={"status": overall, "checks": {"database": db_status, "cache": cache_status}}
    )
