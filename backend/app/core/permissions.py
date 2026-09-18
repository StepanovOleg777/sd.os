from fastapi import Depends, HTTPException, status
from sqlalchemy import select

from backend.app.core.auth import get_current_user
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.role import Role, UserRole
from backend.app.models.user import User


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Role.code)
            .join(
                UserRole,
                UserRole.role_id == Role.id,
            )
            .where(
                UserRole.user_id == user.id
            )
        )

        role_codes = set(
            result.scalars().all()
        )

    if "admin" not in role_codes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав.",
        )

    return user