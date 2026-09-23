from sqlalchemy import select

from backend.app.models.department import Department
from backend.app.services.permission_service import (
    permission_service,
)


CONTACT_PERSONAL_PHONE_CALL = (
    "contact.personal_phone.call"
)


async def _get_department_id_by_name(
    db,
    department_name: str | None,
) -> int | None:
    if not department_name:
        return None

    normalized_name = department_name.strip()

    if not normalized_name:
        return None

    result = await db.execute(
        select(Department.id)
        .where(
            Department.name == normalized_name
        )
        .limit(1)
    )

    return result.scalar_one_or_none()


async def can_call_personal_phone(
    db,
    user_id: int,
    target_department_name: str | None,
) -> bool:
    target_department_id = (
        await _get_department_id_by_name(
            db,
            target_department_name,
        )
    )

    return await permission_service.can_access(
        db=db,
        user_id=user_id,
        permission_code=CONTACT_PERSONAL_PHONE_CALL,
        target_department_id=(
            target_department_id
        ),
    )

