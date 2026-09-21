from collections.abc import Callable

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select

from backend.app.core.auth import get_current_user
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.role import (
    Role,
    UserRole,
)
from backend.app.models.user import User
from backend.app.services.permission_service import (
    permission_service,
)


async def get_user_role_codes(
    user_id: int,
) -> set[str]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Role.code)
            .join(
                UserRole,
                UserRole.role_id == Role.id,
            )
            .where(
                UserRole.user_id == user_id
            )
        )

        return set(
            result.scalars().all()
        )


async def require_admin(
    user: User = Depends(
        get_current_user
    ),
) -> User:
    role_codes = await get_user_role_codes(
        user.id
    )

    if "admin" not in role_codes:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail="Недостаточно прав.",
        )

    return user


def require_permission(
    permission_code: str,
) -> Callable:
    async def dependency(
        user: User = Depends(
            get_current_user
        ),
    ) -> User:
        async with AsyncSessionLocal() as db:
            allowed = (
                await permission_service
                .has_permission(
                    db=db,
                    user_id=user.id,
                    permission_code=(
                        permission_code
                    ),
                )
            )

        if not allowed:
            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail="Недостаточно прав.",
            )

        return user

    return dependency


def require_scoped_permission(
    permission_code: str,
    *,
    target_user_id_param: str | None = None,
    target_department_id_param: str | None = None,
) -> Callable:
    async def dependency(
        user: User = Depends(
            get_current_user
        ),
        **kwargs,
    ) -> User:
        target_user_id = None
        target_department_id = None

        if target_user_id_param is not None:
            target_user_id = kwargs.get(
                target_user_id_param
            )

        if (
            target_department_id_param
            is not None
        ):
            target_department_id = kwargs.get(
                target_department_id_param
            )

        async with AsyncSessionLocal() as db:
            allowed = (
                await permission_service
                .can_access(
                    db=db,
                    user_id=user.id,
                    permission_code=(
                        permission_code
                    ),
                    target_user_id=(
                        target_user_id
                    ),
                    target_department_id=(
                        target_department_id
                    ),
                )
            )

        if not allowed:
            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail="Недостаточно прав.",
            )

        return user

    return dependency