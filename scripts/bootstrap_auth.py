import asyncio
from getpass import getpass

from sqlalchemy import or_, select

from backend.app.models.department import Department
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.security import hash_password
from backend.app.models.role import Role, UserRole
from backend.app.models.user import User


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
        "name": "Собственник",
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


def ask_password() -> str:
    while True:
        password = getpass(
            "Пароль: "
        )

        password_repeat = getpass(
            "Повторите пароль: "
        )

        if not password:
            print(
                "Пароль не может быть пустым."
            )
            continue

        if password != password_repeat:
            print(
                "Пароли не совпадают. "
                "Попробуйте ещё раз."
            )
            continue

        return password


async def create_user(
    role_code: str,
) -> None:
    print()
    print(
        f"Создание пользователя "
        f"с ролью: {role_code}"
    )
    print(
        "-" * 40
    )

    fio = input(
        "ФИО: "
    ).strip()

    email = input(
        "Email: "
    ).strip().lower()

    username = input(
        "Логин: "
    ).strip()

    if not fio:
        print(
            "ФИО не может быть пустым."
        )
        return

    if not email:
        print(
            "Email не может быть пустым."
        )
        return

    if not username:
        print(
            "Логин не может быть пустым."
        )
        return

    password = ask_password()

    async with AsyncSessionLocal() as session:
        existing_result = await session.execute(
            select(User).where(
                or_(
                    User.email == email,
                    User.username == username,
                )
            )
        )

        existing_user = (
            existing_result.scalar_one_or_none()
        )

        if existing_user is not None:
            print()
            print(
                "Пользователь с таким email "
                "или логином уже существует."
            )
            return

        role_result = await session.execute(
            select(Role).where(
                Role.code == role_code
            )
        )

        role = role_result.scalar_one_or_none()

        if role is None:
            print(
                f"Роль {role_code} не найдена."
            )
            return

        user = User(
            fio=fio,
            email=email,
            username=username,
            password_hash=hash_password(
                password
            ),
            status="active",
            is_active=True,
        )

        session.add(user)

        await session.flush()

        user_role = UserRole(
            user_id=user.id,
            role_id=role.id,
        )

        session.add(user_role)

        await session.commit()

        print()
        print(
            f"Пользователь создан: "
            f"{user.fio}"
        )
        print(
            f"Логин: {user.username}"
        )
        print(
            f"Email: {user.email}"
        )
        print(
            f"Роль: {role.name}"
        )


async def main() -> None:
    await create_roles()

    print()
    print(
        "=" * 50
    )
    print(
        "Первичная настройка SD.OS"
    )
    print(
        "=" * 50
    )

    await create_user(
        "developer"
    )

    print()
    print(
        "Первичная настройка завершена."
    )


if __name__ == "__main__":
    asyncio.run(main())