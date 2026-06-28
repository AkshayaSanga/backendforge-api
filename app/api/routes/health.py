from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.redis import get_redis

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    return {"status": "ok", "service": "BackendForge API"}


@router.get("/detailed")
async def detailed_health(db: AsyncSession = Depends(get_db)):
    """Check connectivity to DB and Redis."""
    checks = {}

    try:
        await db.scalar(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
