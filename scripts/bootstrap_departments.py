import asyncio

from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.department import Department


DEPARTMENTS = [
    "Отдел бухгалтерского учета",
    "Отдел закупок",
    "Отдел ИТ",
    "Отдел развития",
    "Отдел по работе с внешними и внутренними коммуникациями",
    "Отдел продаж «Дистрибуция»",
    "Отдел продаж ДНР/ЛНР",
    "Отдел продаж «Заря»",
    "Отдел продаж «Николаевка»",
    "Отдел продаж «Покровское»",
    "Отдел продаж ТК «Октябрьская»",
    "Маркетинг",
    "Недвижимость",
    "СЕО",
    "Сопроводительные подразделения",
    "Служба логистики",
    "Складская логистика",
    "Автоколонна",
]


async def main() -> None:
    async with AsyncSessionLocal() as db:
        for department_name in DEPARTMENTS:
            result = await db.execute(
                select(Department).where(
                    Department.name == department_name
                )
            )

            existing_department = (
                result.scalar_one_or_none()
            )

            if existing_department is not None:
                continue

            db.add(
                Department(
                    name=department_name,
                    is_active=True,
                )
            )

        await db.commit()

    print("Отделы успешно добавлены.")


if __name__ == "__main__":
    asyncio.run(main())