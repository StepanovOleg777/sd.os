from copy import deepcopy

from sqlalchemy import select

from backend.app.models.department import Department
from backend.app.services.permission_service import (
    permission_service,
)


DIRECTORY_PERSONAL_PHONE_VIEW = (
    "directory.personal_phone.view"
)

DIRECTORY_NOTE_VIEW = (
    "directory.note.view"
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


async def can_view_personal_phone(
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
        permission_code=(
            DIRECTORY_PERSONAL_PHONE_VIEW
        ),
        target_department_id=(
            target_department_id
        ),
    )


async def can_view_directory_note(
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
        permission_code=DIRECTORY_NOTE_VIEW,
        target_department_id=(
            target_department_id
        ),
    )


async def filter_directory_contact(
    db,
    user_id: int,
    contact: dict,
) -> dict:
    result = deepcopy(contact)

    department_name = (
        result.get("department")
        or ""
    )

    personal_phone_allowed = (
        await can_view_personal_phone(
            db=db,
            user_id=user_id,
            target_department_name=(
                department_name
            ),
        )
    )

    note_allowed = (
        await can_view_directory_note(
            db=db,
            user_id=user_id,
            target_department_name=(
                department_name
            ),
        )
    )

    phones = result.get("phones")

    if isinstance(phones, dict):
        if not personal_phone_allowed:
            phones.pop(
                "personal",
                None,
            )

    if not note_allowed:
        result.pop(
            "note",
            None,
        )

    return result


async def filter_directory_contacts(
    db,
    user_id: int,
    contacts: list[dict],
) -> list[dict]:
    filtered_contacts = []

    for contact in contacts:
        filtered_contact = (
            await filter_directory_contact(
                db=db,
                user_id=user_id,
                contact=contact,
            )
        )

        filtered_contacts.append(
            filtered_contact
        )

    return filtered_contacts

