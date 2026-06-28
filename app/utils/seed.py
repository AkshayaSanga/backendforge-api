import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


async def seed_admin(db: AsyncSession) -> None:
    existing = await db.scalar(select(User).where(User.email == settings.ADMIN_EMAIL))
    if existing:
        logger.info("Admin user already exists — skipping seed")
        return

    admin = User(
        email=settings.ADMIN_EMAIL,
        full_name=settings.ADMIN_FULL_NAME,
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        role=UserRole.admin,
        is_active=True,
        is_verified=True,
    )
    db.add(admin)
    await db.commit()
    logger.info(f"Admin user seeded: {settings.ADMIN_EMAIL}")


async def run_seed() -> None:
    async with AsyncSessionLocal() as db:
        await seed_admin(db)


if __name__ == "__main__":
    asyncio.run(run_seed())
