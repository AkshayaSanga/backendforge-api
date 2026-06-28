import json
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.models.user import User, UserRole
from app.schemas.user import UserOut


PROFILE_CACHE_TTL = 300  # 5 minutes


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        return await self.db.get(User, user_id)

    async def get_profile_cached(self, user_id: UUID) -> Optional[UserOut]:
        redis = await get_redis()
        cache_key = f"profile:{user_id}"

        cached = await redis.get(cache_key)
        if cached:
            return UserOut.model_validate(json.loads(cached))

        user = await self.get_by_id(user_id)
        if not user:
            return None

        out = UserOut.model_validate(user)
        await redis.setex(cache_key, PROFILE_CACHE_TTL, out.model_dump_json())
        return out

    async def invalidate_profile_cache(self, user_id: UUID) -> None:
        redis = await get_redis()
        await redis.delete(f"profile:{user_id}")

    async def update_profile(
        self,
        user_id: UUID,
        full_name: Optional[str] = None,
        bio: Optional[str] = None,
    ) -> User:
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        if full_name is not None:
            user.full_name = full_name
        if bio is not None:
            user.bio = bio

        await self.db.flush()
        await self.invalidate_profile_cache(user_id)
        return user

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        role: Optional[UserRole] = None,
    ) -> Tuple[List[User], int]:
        query = select(User)
        count_query = select(func.count()).select_from(User)

        if role:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)

        total = await self.db.scalar(count_query) or 0
        users = await self.db.scalars(
            query.offset((page - 1) * page_size).limit(page_size).order_by(User.created_at.desc())
        )
        return list(users.all()), total

    async def admin_update_user(
        self,
        user_id: UUID,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> User:
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active

        await self.db.flush()
        await self.invalidate_profile_cache(user_id)
        return user
