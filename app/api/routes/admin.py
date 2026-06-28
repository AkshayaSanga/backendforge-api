from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db
from app.db.redis import get_redis
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.get("/dashboard")
async def admin_dashboard(db: AsyncSession = Depends(get_db)):
    """[Admin] System dashboard with DB and Redis stats."""
    redis = await get_redis()

    user_count = await db.scalar(text("SELECT COUNT(*) FROM users"))
    file_count = await db.scalar(text("SELECT COUNT(*) FROM uploaded_files"))
    token_count = await db.scalar(text("SELECT COUNT(*) FROM refresh_tokens WHERE is_revoked = false"))
    redis_info = await redis.info("server")

    return {
        "users": user_count,
        "uploaded_files": file_count,
        "active_refresh_tokens": token_count,
        "redis_version": redis_info.get("redis_version"),
    }
