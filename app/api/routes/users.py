from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin, require_manager_or_above
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import AdminUserUpdateRequest, UserListResponse, UserOut, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the currently authenticated user's profile (cached)."""
    service = UserService(db)
    return await service.get_profile_cached(current_user.id)


@router.patch("/me", response_model=UserOut)
async def update_my_profile(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update name or bio for the currently authenticated user."""
    service = UserService(db)
    try:
        user = await service.update_profile(current_user.id, body.full_name, body.bio)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return user


@router.get("", response_model=UserListResponse, dependencies=[Depends(require_manager_or_above)])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """[Manager+] List all users with optional role filter."""
    service = UserService(db)
    users, total = await service.list_users(page=page, page_size=page_size, role=role)
    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=users,
    )


@router.get("/{user_id}", response_model=UserOut, dependencies=[Depends(require_manager_or_above)])
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """[Manager+] Get a specific user by ID."""
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut, dependencies=[Depends(require_admin)])
async def admin_update_user(
    user_id: UUID,
    body: AdminUserUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """[Admin] Update a user's role or active status."""
    service = UserService(db)
    try:
        user = await service.admin_update_user(user_id, body.role, body.is_active)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return user
