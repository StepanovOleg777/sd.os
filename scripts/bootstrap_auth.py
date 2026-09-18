import asyncio

from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.role import Role


ROLES = [
    {
        "code": "admin",
        "name": "Администратор",
    },
    {
        "code": "developer",
        "name": "Разработчик",
    },
    {
        "code": "director",
        "name": "Руководитель",
    },
    {
        "code": "department_head",
        "name": "Руководитель отдела",
    },
    {
        "code": "employee",
        "name": "Сотрудник",
    },
]


async def create_roles() -> None:
    async with AsyncSessionLocal() as session:
        for role_data in ROLES:
            result = await session.execute(
                select(Role).where(
                    Role.code == role_data["code"]
                )
            )

            role = result.scalar_one_or_none()

            if role is not None:
                print(
                    f"Роль уже существует: "
                    f"{role_data['code']}"
                )
                continue

            role = Role(
                code=role_data["code"],
                name=role_data["name"],
            )

            session.add(role)

            print(
                f"Создана роль: "
                f"{role_data['code']}"
            )

        await session.commit()


async def main() -> None:
    await create_roles()


if __name__ == "__main__":
    asyncio.run(main())