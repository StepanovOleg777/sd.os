from dataclasses import dataclass

from sqlalchemy import select

from backend.app.models.permission import (
    Permission,
    RolePermission,
    UserPermission,
    UserPermissionTarget,
)
from backend.app.models.role import UserRole
from backend.app.models.user import User


@dataclass
class PermissionGrant:
    permission_code: str
    scope_type: str
    source: str
    source_id: int
    targets: set[tuple[str, int]]


class PermissionService:
    VALID_SCOPES = {
        "all",
        "own_department",
        "selected_departments",
        "all_departments",
        "selected_users",
        "all_users",
    }

    TARGET_DEPARTMENT = "department"
    TARGET_USER = "user"

    async def get_user(
        self,
        db,
        user_id: int,
    ) -> User | None:
        result = await db.execute(
            select(User).where(
                User.id == user_id
            )
        )

        return result.scalar_one_or_none()

    async def get_role_grants(
        self,
        db,
        user_id: int,
        permission_code: str | None = None,
    ) -> list[PermissionGrant]:
        query = (
            select(
                RolePermission,
                Permission,
            )
            .join(
                Permission,
                Permission.id
                == RolePermission.permission_id,
            )
            .join(
                UserRole,
                UserRole.role_id
                == RolePermission.role_id,
            )
            .where(
                UserRole.user_id == user_id
            )
        )

        if permission_code is not None:
            query = query.where(
                Permission.code
                == permission_code
            )

        result = await db.execute(
            query
        )

        rows = result.all()

        grants = []

        for (
            role_permission,
            permission,
        ) in rows:
            grants.append(
                PermissionGrant(
                    permission_code=permission.code,
                    scope_type=(
                        role_permission.scope_type
                    ),
                    source="role",
                    source_id=(
                        role_permission.role_id
                    ),
                    targets=set(),
                )
            )

        return grants

    async def get_user_grants(
        self,
        db,
        user_id: int,
        permission_code: str | None = None,
    ) -> list[PermissionGrant]:
        query = (
            select(
                UserPermission,
                Permission,
            )
            .join(
                Permission,
                Permission.id
                == UserPermission.permission_id,
            )
            .where(
                UserPermission.user_id
                == user_id
            )
        )

        if permission_code is not None:
            query = query.where(
                Permission.code
                == permission_code
            )

        result = await db.execute(
            query
        )

        rows = result.all()

        grants = []

        for (
            user_permission,
            permission,
        ) in rows:
            targets_result = await db.execute(
                select(
                    UserPermissionTarget
                ).where(
                    UserPermissionTarget.user_permission_id
                    == user_permission.id
                )
            )

            target_rows = (
                targets_result.scalars().all()
            )

            targets = {
                (
                    target.target_type,
                    target.target_id,
                )
                for target in target_rows
            }

            grants.append(
                PermissionGrant(
                    permission_code=permission.code,
                    scope_type=(
                        user_permission.scope_type
                    ),
                    source="user",
                    source_id=(
                        user_permission.id
                    ),
                    targets=targets,
                )
            )

        return grants

    async def get_effective_permissions(
        self,
        db,
        user_id: int,
    ) -> dict[str, list[PermissionGrant]]:
        grants = []

        grants.extend(
            await self.get_role_grants(
                db,
                user_id,
            )
        )

        grants.extend(
            await self.get_user_grants(
                db,
                user_id,
            )
        )

        permissions = {}

        for grant in grants:
            permissions.setdefault(
                grant.permission_code,
                [],
            )

            permissions[
                grant.permission_code
            ].append(
                grant
            )

        return permissions

    async def has_permission(
        self,
        db,
        user_id: int,
        permission_code: str,
    ) -> bool:
        role_grants = await self.get_role_grants(
            db,
            user_id,
            permission_code,
        )

        if role_grants:
            return True

        user_grants = await self.get_user_grants(
            db,
            user_id,
            permission_code,
        )

        return bool(
            user_grants
        )

    async def get_permission_grants(
        self,
        db,
        user_id: int,
        permission_code: str,
    ) -> list[PermissionGrant]:
        grants = []

        grants.extend(
            await self.get_role_grants(
                db,
                user_id,
                permission_code,
            )
        )

        grants.extend(
            await self.get_user_grants(
                db,
                user_id,
                permission_code,
            )
        )

        return grants

    async def get_target_user(
        self,
        db,
        target_user_id: int,
    ) -> User | None:
        result = await db.execute(
            select(User).where(
                User.id == target_user_id
            )
        )

        return result.scalar_one_or_none()

    async def can_access(
        self,
        db,
        user_id: int,
        permission_code: str,
        target_user_id: int | None = None,
        target_department_id: int | None = None,
    ) -> bool:
        user = await self.get_user(
            db,
            user_id,
        )

        if user is None:
            return False

        if (
            user.status != "active"
            or not user.is_active
        ):
            return False

        grants = await self.get_permission_grants(
            db,
            user_id,
            permission_code,
        )

        if not grants:
            return False

        resolved_target_department_id = (
            target_department_id
        )

        if (
            target_user_id is not None
            and resolved_target_department_id
            is None
        ):
            target_user = (
                await self.get_target_user(
                    db,
                    target_user_id,
                )
            )

            if target_user is None:
                return False

            resolved_target_department_id = (
                target_user.department_id
            )

        for grant in grants:
            if grant.scope_type not in self.VALID_SCOPES:
                continue

            if grant.scope_type == "all":
                return True

            if (
                grant.scope_type
                == "all_departments"
            ):
                if (
                    resolved_target_department_id
                    is not None
                ):
                    return True

            if (
                grant.scope_type
                == "all_users"
            ):
                if target_user_id is not None:
                    return True

            if (
                grant.scope_type
                == "own_department"
            ):
                if (
                    user.department_id
                    is not None
                    and resolved_target_department_id
                    == user.department_id
                ):
                    return True

            if (
                grant.scope_type
                == "selected_departments"
            ):
                if (
                    resolved_target_department_id
                    is not None
                    and (
                        self.TARGET_DEPARTMENT,
                        resolved_target_department_id,
                    )
                    in grant.targets
                ):
                    return True

            if (
                grant.scope_type
                == "selected_users"
            ):
                if (
                    target_user_id is not None
                    and (
                        self.TARGET_USER,
                        target_user_id,
                    )
                    in grant.targets
                ):
                    return True

        return False

    async def can_use_feature(
        self,
        db,
        user_id: int,
        permission_code: str,
    ) -> bool:
        return await self.has_permission(
            db,
            user_id,
            permission_code,
        )


permission_service = PermissionService()