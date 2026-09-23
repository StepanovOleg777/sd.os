import asyncio

from sqlalchemy import delete, select

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.permission import (
    Permission,
    RolePermission,
)
from backend.app.models.role import Role


PERMISSIONS = [
    {
        "code": "users.view",
        "name": "Просмотр пользователей",
        "description": (
            "Позволяет видеть список пользователей "
            "и их карточки."
        ),
    },
    {
        "code": "users.invite",
        "name": "Приглашение пользователей",
        "description": (
            "Позволяет приглашать новых пользователей "
            "в SD.OS."
        ),
    },
    {
        "code": "users.edit",
        "name": "Редактирование пользователей",
        "description": (
            "Позволяет изменять данные, статус "
            "и отдел пользователя."
        ),
    },
    {
        "code": "users.roles.manage",
        "name": "Управление ролями пользователей",
        "description": (
            "Позволяет назначать и снимать роли "
            "у пользователей."
        ),
    },
    {
        "code": "departments.view",
        "name": "Просмотр отделов",
        "description": (
            "Позволяет видеть список отделов."
        ),
    },
    {
        "code": "departments.manage",
        "name": "Управление отделами",
        "description": (
            "Позволяет создавать, переименовывать, "
            "включать и отключать отделы."
        ),
    },
    {
        "code": "audit.view",
        "name": "Просмотр журнала аудита",
        "description": (
            "Позволяет просматривать журнал "
            "изменений и административных действий."
        ),
    },
    {
        "code": "directory.personal_phone.view",
        "name": "Просмотр личных телефонов",
        "description": (
            "Позволяет видеть личные номера сотрудников "
            "в корпоративном справочнике."
        ),
    },
    {
        "code": "directory.note.view",
        "name": "Просмотр служебных заметок справочника",
        "description": (
            "Позволяет видеть служебные заметки "
            "корпоративного справочника."
        ),
    },
    {
        "code": "contact.personal_phone.call",
        "name": "Звонки на личные номера",
        "description": (
            "Позволяет использовать личный номер сотрудника "
            "для звонка, если корпоративный номер отсутствует."
        ),
    },
    {
        "code": "chat.use",
        "name": "Доступ к сообщениям",
        "description": (
            "Позволяет пользоваться внутренним "
            "мессенджером SD.OS."
        ),
    },
    {
        "code": "chat.message.send",
        "name": "Отправка сообщений",
        "description": (
            "Позволяет отправлять обычные сообщения "
            "пользователям SD.OS."
        ),
    },
    {
        "code": "chat.announcement.department",
        "name": "Объявления отдела",
        "description": (
            "Позволяет публиковать важные сообщения "
            "для отдела."
        ),
    },
    {
        "code": "chat.announcement.company",
        "name": "Объявления всей организации",
        "description": (
            "Позволяет публиковать важные сообщения "
            "для всей организации."
        ),
    },
]


ROLE_PERMISSIONS = {
    "director": {
        "users.view": "all",
        "users.invite": "all",
        "users.edit": "all",
        "users.roles.manage": "all",
        "departments.view": "all",
        "departments.manage": "all",
        "audit.view": "all",
        "chat.use": "all",
        "chat.message.send": "all",
        "chat.announcement.department": "all_departments",
        "chat.announcement.company": "all",
        "directory.personal_phone.view": "all",
        "directory.note.view": "all",
        "contact.personal_phone.call": "all",
    },

    "developer": {
        "users.view": "all",
        "users.invite": "all",
        "users.edit": "all",
        "users.roles.manage": "all",
        "departments.view": "all",
        "departments.manage": "all",
        "audit.view": "all",
        "chat.use": "all",
        "chat.message.send": "all",
        "chat.announcement.department": "all_departments",
        "chat.announcement.company": "all",
        "directory.personal_phone.view": "all",
        "directory.note.view": "all",
        "contact.personal_phone.call": "all",
    },

    "admin": {
        "users.view": "all",
        "users.invite": "all",
        "users.edit": "all",
        "users.roles.manage": "all",
        "departments.view": "all",
        "departments.manage": "all",
        "audit.view": "all",
        "chat.use": "all",
        "chat.message.send": "all",
        "directory.personal_phone.view": "all",
        "directory.note.view": "all",
        "contact.personal_phone.call": "all",
    },

    "department_head": {
        "users.view": "own_department",
        "users.invite": "own_department",
        "users.edit": "own_department",
        "chat.use": "all",
        "chat.message.send": "all",
        "chat.announcement.department": "own_department",
        "directory.personal_phone.view": "all",
        "directory.note.view": "all",
        "contact.personal_phone.call": "all",
    },

    "employee": {
    },
}


async def get_role(
    db,
    role_code: str,
) -> Role | None:
    result = await db.execute(
        select(Role).where(
            Role.code == role_code
        )
    )

    return result.scalar_one_or_none()


async def get_permission(
    db,
    permission_code: str,
) -> Permission | None:
    result = await db.execute(
        select(Permission).where(
            Permission.code == permission_code
        )
    )

    return result.scalar_one_or_none()


async def bootstrap_permissions() -> None:
    async with AsyncSessionLocal() as db:
        for permission_data in PERMISSIONS:
            existing_permission = (
                await get_permission(
                    db,
                    permission_data["code"],
                )
            )

            if existing_permission is None:
                db.add(
                    Permission(
                        code=permission_data["code"],
                        name=permission_data["name"],
                        description=(
                            permission_data[
                                "description"
                            ]
                        ),
                    )
                )

            else:
                existing_permission.name = (
                    permission_data["name"]
                )

                existing_permission.description = (
                    permission_data[
                        "description"
                    ]
                )

        await db.flush()

        for (
            role_code,
            role_permissions,
        ) in ROLE_PERMISSIONS.items():
            role = await get_role(
                db,
                role_code,
            )

            if role is None:
                print(
                    f"Роль '{role_code}' не найдена. "
                    f"Пропускаем."
                )
                continue

            await db.execute(
                delete(RolePermission).where(
                    RolePermission.role_id
                    == role.id
                )
            )

            for (
                permission_code,
                scope_type,
            ) in role_permissions.items():
                permission = (
                    await get_permission(
                        db,
                        permission_code,
                    )
                )

                if permission is None:
                    raise RuntimeError(
                        "Permission не найден: "
                        f"{permission_code}"
                    )

                db.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=(
                            permission.id
                        ),
                        scope_type=scope_type,
                    )
                )

        await db.commit()

    print(
        "Permissions и стандартные права ролей "
        "успешно настроены."
    )


if __name__ == "__main__":
    asyncio.run(
        bootstrap_permissions()
    )