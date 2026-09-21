import math
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)
from fastapi.templating import Jinja2Templates
from sqlalchemy import (
    delete,
    func,
    select,
)

from backend.app.core.config import (
    TEMPLATES_DIR,
    settings,
)
from backend.app.core.database import (
    AsyncSessionLocal,
)
from backend.app.core.permissions import (
    require_permission,
)
from backend.app.models.audit_log import AuditLog
from backend.app.models.department import Department
from backend.app.models.invite import Invite
from backend.app.models.role import (
    Role,
    UserRole,
)
from backend.app.models.session import Session
from backend.app.models.user import User
from backend.app.services.audit_service import (
    audit_service,
)
from backend.app.services.email_service import (
    EmailServiceError,
    email_service,
)
from backend.app.services.invite_service import (
    invite_service,
)
from backend.app.services.permission_service import (
    permission_service,
)


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)

templates = Jinja2Templates(
    directory=TEMPLATES_DIR
)


USER_VIEWS = {
    "active": {
        "title": "Активные",
        "statuses": ["active"],
    },
    "invited": {
        "title": "Приглашённые",
        "statuses": ["invited"],
    },
    "disabled": {
        "title": "Отключённые",
        "statuses": ["disabled"],
    },
    "archive": {
        "title": "Архив",
        "statuses": ["dismissed"],
    },
}


ROLES_REQUIRING_DEPARTMENT = {
    "employee",
    "department_head",
}


PROTECTED_ROLE_CODES = {
    "director",
    "developer",
}


AUDIT_PAGE_SIZE = 50


# =========================================================
# COMMON HELPERS
# =========================================================


async def get_all_roles(
    db,
) -> list[Role]:
    result = await db.execute(
        select(Role).order_by(
            Role.name
        )
    )

    return list(
        result.scalars().all()
    )


async def get_role_codes(
    db,
    user_id: int,
) -> set[str]:
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


async def get_user_roles(
    db,
    user_id: int,
) -> list[Role]:
    result = await db.execute(
        select(Role)
        .join(
            UserRole,
            UserRole.role_id == Role.id,
        )
        .where(
            UserRole.user_id == user_id
        )
        .order_by(
            Role.name
        )
    )

    return list(
        result.scalars().all()
    )


async def get_user_role_ids(
    db,
    user_id: int,
) -> set[int]:
    result = await db.execute(
        select(UserRole.role_id).where(
            UserRole.user_id == user_id
        )
    )

    return set(
        result.scalars().all()
    )


async def get_departments(
    db,
    active_only: bool = True,
) -> list[Department]:
    query = select(
        Department
    )

    if active_only:
        query = query.where(
            Department.is_active.is_(True)
        )

    query = query.order_by(
        Department.name
    )

    result = await db.execute(
        query
    )

    return list(
        result.scalars().all()
    )


async def get_department_by_id(
    db,
    department_id: int | None,
) -> Department | None:
    if department_id is None:
        return None

    result = await db.execute(
        select(Department).where(
            Department.id == department_id
        )
    )

    return result.scalar_one_or_none()


async def get_user_by_id(
    db,
    user_id: int,
) -> User | None:
    result = await db.execute(
        select(User).where(
            User.id == user_id
        )
    )

    return result.scalar_one_or_none()


def roles_require_department(
    selected_roles: list[Role],
) -> bool:
    role_codes = {
        role.code
        for role in selected_roles
    }

    return bool(
        role_codes
        & ROLES_REQUIRING_DEPARTMENT
    )


def parse_department_id(
    raw_department_id: str,
) -> int | None:
    value = raw_department_id.strip()

    if not value:
        return None

    try:
        return int(
            value
        )

    except ValueError:
        return None


async def validate_department(
    db,
    department_id: int | None,
    required: bool,
) -> tuple[Department | None, str | None]:
    if department_id is None:
        if required:
            return (
                None,
                "Для выбранной роли необходимо "
                "указать отдел.",
            )

        return (
            None,
            None,
        )

    department = await get_department_by_id(
        db,
        department_id,
    )

    if department is None:
        return (
            None,
            "Выбранный отдел не найден.",
        )

    if not department.is_active:
        return (
            None,
            "Выбранный отдел отключён.",
        )

    return (
        department,
        None,
    )


async def ensure_scoped_access(
    db,
    actor: User,
    permission_code: str,
    *,
    target_user_id: int | None = None,
    target_department_id: int | None = None,
) -> None:
    allowed = await permission_service.can_access(
        db=db,
        user_id=actor.id,
        permission_code=permission_code,
        target_user_id=target_user_id,
        target_department_id=target_department_id,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав.",
        )


async def actor_can_manage_roles(
    db,
    actor: User,
) -> bool:
    return await permission_service.has_permission(
        db=db,
        user_id=actor.id,
        permission_code="users.roles.manage",
    )


async def get_roles_available_for_actor(
    db,
    actor: User,
) -> list[Role]:
    all_roles = await get_all_roles(
        db
    )

    actor_role_codes = await get_role_codes(
        db,
        actor.id,
    )

    if "director" in actor_role_codes:
        return all_roles

    can_manage_roles = (
        await actor_can_manage_roles(
            db,
            actor,
        )
    )

    if can_manage_roles:
        return [
            role
            for role in all_roles
            if role.code
            not in PROTECTED_ROLE_CODES
        ]

    return [
        role
        for role in all_roles
        if role.code == "employee"
    ]


async def validate_role_assignment(
    db,
    actor: User,
    current_role_codes: set[str],
    selected_roles: list[Role],
) -> str | None:
    selected_role_codes = {
        role.code
        for role in selected_roles
    }

    actor_role_codes = await get_role_codes(
        db,
        actor.id,
    )

    if "director" in actor_role_codes:
        return None

    protected_changes = (
        current_role_codes
        ^ selected_role_codes
    ) & PROTECTED_ROLE_CODES

    if protected_changes:
        return (
            "Назначать или снимать роли "
            "«Руководитель» и «Разработчик» "
            "может только руководитель."
        )

    can_manage_roles = (
        await actor_can_manage_roles(
            db,
            actor,
        )
    )

    if can_manage_roles:
        return None

    if selected_role_codes != current_role_codes:
        return (
            "У вас нет права изменять роли "
            "пользователя."
        )

    return None


async def validate_new_user_roles(
    db,
    actor: User,
    selected_roles: list[Role],
) -> str | None:
    selected_codes = {
        role.code
        for role in selected_roles
    }

    actor_role_codes = await get_role_codes(
        db,
        actor.id,
    )

    if "director" in actor_role_codes:
        return None

    if selected_codes & PROTECTED_ROLE_CODES:
        return (
            "Назначать роли «Руководитель» "
            "и «Разработчик» может только "
            "руководитель."
        )

    can_manage_roles = (
        await actor_can_manage_roles(
            db,
            actor,
        )
    )

    if can_manage_roles:
        return None

    if selected_codes != {"employee"}:
        return (
            "Вы можете приглашать пользователя "
            "только с ролью «Сотрудник»."
        )

    return None


async def get_departments_available_for_actor(
    db,
    actor: User,
) -> list[Department]:
    all_departments = await get_departments(
        db,
        active_only=True,
    )

    grants = (
        await permission_service
        .get_permission_grants(
            db,
            actor.id,
            "users.invite",
        )
    )

    if any(
        grant.scope_type
        in {
            "all",
            "all_departments",
        }
        for grant in grants
    ):
        return all_departments

    if any(
        grant.scope_type
        == "own_department"
        for grant in grants
    ):
        if actor.department_id is None:
            return []

        return [
            department
            for department in all_departments
            if department.id
            == actor.department_id
        ]

    allowed_department_ids: set[int] = set()

    for grant in grants:
        if grant.scope_type != "selected_departments":
            continue

        for (
            target_type,
            target_id,
        ) in grant.targets:
            if target_type == "department":
                allowed_department_ids.add(
                    target_id
                )

    return [
        department
        for department in all_departments
        if department.id
        in allowed_department_ids
    ]


async def get_edit_departments_for_actor(
    db,
    actor: User,
) -> list[Department]:
    all_departments = await get_departments(
        db,
        active_only=False,
    )

    grants = (
        await permission_service
        .get_permission_grants(
            db,
            actor.id,
            "users.edit",
        )
    )

    if any(
        grant.scope_type
        in {
            "all",
            "all_departments",
        }
        for grant in grants
    ):
        return all_departments

    if any(
        grant.scope_type
        == "own_department"
        for grant in grants
    ):
        if actor.department_id is None:
            return []

        return [
            department
            for department in all_departments
            if department.id
            == actor.department_id
        ]

    allowed_department_ids: set[int] = set()

    for grant in grants:
        if grant.scope_type != "selected_departments":
            continue

        for (
            target_type,
            target_id,
        ) in grant.targets:
            if target_type == "department":
                allowed_department_ids.add(
                    target_id
                )

    return [
        department
        for department in all_departments
        if department.id
        in allowed_department_ids
    ]


def build_user_audit_state(
    user: User,
    role_codes: set[str],
) -> dict:
    return {
        "fio": user.fio,
        "email": user.email,
        "username": user.username,
        "status": user.status,
        "is_active": user.is_active,
        "department_id": user.department_id,
        "roles": sorted(
            role_codes
        ),
    }


def get_status_label(
    status_code: str | None,
) -> str:
    labels = {
        "active": "Активен",
        "invited": "Приглашён",
        "disabled": "Отключён",
        "dismissed": "Уволен",
    }

    if status_code is None:
        return "—"

    return labels.get(
        status_code,
        status_code,
    )


async def get_department_name(
    db,
    department_id: int | None,
) -> str:
    if department_id is None:
        return "Без отдела"

    department = await get_department_by_id(
        db,
        department_id,
    )

    if department is None:
        return f"Отдел #{department_id}"

    return department.name


async def get_role_names_by_codes(
    db,
    role_codes: list[str] | set[str],
) -> str:
    if not role_codes:
        return "Без ролей"

    result = await db.execute(
        select(Role).where(
            Role.code.in_(
                role_codes
            )
        )
    )

    roles = list(
        result.scalars().all()
    )

    role_names = sorted(
        role.name
        for role in roles
    )

    if not role_names:
        return ", ".join(
            sorted(role_codes)
        )

    return ", ".join(
        role_names
    )


async def build_audit_diff(
    db,
    before_data: dict | None,
    after_data: dict | None,
) -> tuple[list[str], list[str]]:
    before_data = before_data or {}
    after_data = after_data or {}

    before_lines = []
    after_lines = []

    all_keys = set(
        before_data.keys()
    ) | set(
        after_data.keys()
    )

    for key in sorted(all_keys):
        before_value = before_data.get(
            key
        )

        after_value = after_data.get(
            key
        )

        if before_value == after_value:
            continue

        if key == "department_id":
            before_text = (
                await get_department_name(
                    db,
                    before_value,
                )
            )

            after_text = (
                await get_department_name(
                    db,
                    after_value,
                )
            )

            label = "Отдел"

        elif key == "roles":
            before_text = (
                await get_role_names_by_codes(
                    db,
                    before_value or [],
                )
            )

            after_text = (
                await get_role_names_by_codes(
                    db,
                    after_value or [],
                )
            )

            label = "Роли"

        elif key == "status":
            before_text = (
                get_status_label(
                    before_value
                )
            )

            after_text = (
                get_status_label(
                    after_value
                )
            )

            label = "Статус"

        elif key == "is_active":
            before_text = (
                "Да"
                if before_value
                else "Нет"
            )

            after_text = (
                "Да"
                if after_value
                else "Нет"
            )

            label = "Активен"

        elif key == "fio":
            before_text = (
                before_value or "—"
            )

            after_text = (
                after_value or "—"
            )

            label = "ФИО"

        elif key == "email":
            before_text = (
                before_value or "—"
            )

            after_text = (
                after_value or "—"
            )

            label = "Email"

        elif key == "username":
            before_text = (
                before_value or "—"
            )

            after_text = (
                after_value or "—"
            )

            label = "Логин"

        elif key == "name":
            before_text = (
                before_value or "—"
            )

            after_text = (
                after_value or "—"
            )

            label = "Название"

        else:
            before_text = (
                str(before_value)
                if before_value is not None
                else "—"
            )

            after_text = (
                str(after_value)
                if after_value is not None
                else "—"
            )

            label = key

        before_lines.append(
            f"{label}: {before_text}"
        )

        after_lines.append(
            f"{label}: {after_text}"
        )

    return (
        before_lines,
        after_lines,
    )


# =========================================================
# USERS DATA
# =========================================================


async def get_users_data(
    view: str,
    actor: User,
) -> list[dict]:
    view_data = USER_VIEWS.get(
        view,
        USER_VIEWS["active"],
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User)
            .where(
                User.status.in_(
                    view_data["statuses"]
                )
            )
            .order_by(
                User.fio
            )
        )

        users = list(
            result.scalars().all()
        )

        users_data = []

        for user in users:
            can_view = (
                await permission_service
                .can_access(
                    db=db,
                    user_id=actor.id,
                    permission_code="users.view",
                    target_user_id=user.id,
                )
            )

            if not can_view:
                continue

            roles = await get_user_roles(
                db,
                user.id,
            )

            department = (
                await get_department_by_id(
                    db,
                    user.department_id,
                )
            )

            users_data.append(
                {
                    "user": user,
                    "roles": roles,
                    "department": department,
                }
            )

        return users_data


async def get_departments_data(
    db,
) -> list[dict]:
    departments = await get_departments(
        db,
        active_only=False,
    )

    departments_data = []

    for department in departments:
        total_users_result = await db.execute(
            select(
                func.count(User.id)
            ).where(
                User.department_id
                == department.id
            )
        )

        total_users = (
            total_users_result.scalar_one()
        )

        active_users_result = await db.execute(
            select(
                func.count(User.id)
            ).where(
                User.department_id
                == department.id,
                User.status.in_(
                    [
                        "active",
                        "invited",
                    ]
                ),
            )
        )

        active_users = (
            active_users_result.scalar_one()
        )

        departments_data.append(
            {
                "department": department,
                "total_users": total_users,
                "active_users": active_users,
            }
        )

    return departments_data


# =========================================================
# USERS
# =========================================================


@router.get(
    "/users",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def users_page(
    request: Request,
    view: str = "active",
    actor: User = Depends(
        require_permission(
            "users.view"
        )
    ),
):
    if view not in USER_VIEWS:
        view = "active"

    users = await get_users_data(
        view,
        actor,
    )

    async with AsyncSessionLocal() as db:
        can_invite = (
            await permission_service
            .has_permission(
                db,
                actor.id,
                "users.invite",
            )
        )

        can_view_departments = (
            await permission_service
            .has_permission(
                db,
                actor.id,
                "departments.view",
            )
        )

        can_view_audit = (
            await permission_service
            .has_permission(
                db,
                actor.id,
                "audit.view",
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="admin/users.html",
        context={
            "admin": actor,
            "users": users,
            "current_view": view,
            "views": USER_VIEWS,
            "can_invite": can_invite,
            "can_view_departments": (
                can_view_departments
            ),
            "can_view_audit": (
                can_view_audit
            ),
        },
    )


@router.get(
    "/users/new",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def user_create_page(
    request: Request,
    actor: User = Depends(
        require_permission(
            "users.invite"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        roles = (
            await get_roles_available_for_actor(
                db,
                actor,
            )
        )

        departments = (
            await get_departments_available_for_actor(
                db,
                actor,
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="admin/user_create.html",
        context={
            "admin": actor,
            "roles": roles,
            "departments": departments,
            "error": None,
            "invite_url": None,
            "created_user": None,
            "email_sent": False,
            "email_error": None,
        },
    )


@router.post(
    "/users/new",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def user_create(
    request: Request,
    fio: str = Form(...),
    email: str = Form(...),
    roles: list[str] = Form(...),
    department_id: str = Form(""),
    actor: User = Depends(
        require_permission(
            "users.invite"
        )
    ),
):
    fio = fio.strip()
    email = email.strip().lower()

    parsed_department_id = (
        parse_department_id(
            department_id
        )
    )

    async with AsyncSessionLocal() as db:
        available_roles = (
            await get_roles_available_for_actor(
                db,
                actor,
            )
        )

        departments = (
            await get_departments_available_for_actor(
                db,
                actor,
            )
        )

        base_context = {
            "admin": actor,
            "roles": available_roles,
            "departments": departments,
            "invite_url": None,
            "created_user": None,
            "email_sent": False,
            "email_error": None,
        }

        if not fio:
            return templates.TemplateResponse(
                request=request,
                name="admin/user_create.html",
                context={
                    **base_context,
                    "error": "Укажите ФИО.",
                },
                status_code=400,
            )

        if not email:
            return templates.TemplateResponse(
                request=request,
                name="admin/user_create.html",
                context={
                    **base_context,
                    "error": "Укажите email.",
                },
                status_code=400,
            )

        existing_result = await db.execute(
            select(User).where(
                User.email == email
            )
        )

        existing_user = (
            existing_result.scalar_one_or_none()
        )

        if existing_user is not None:
            return templates.TemplateResponse(
                request=request,
                name="admin/user_create.html",
                context={
                    **base_context,
                    "error": (
                        "Пользователь с таким "
                        "email уже существует."
                    ),
                },
                status_code=400,
            )

        selected_roles_result = await db.execute(
            select(Role).where(
                Role.code.in_(
                    roles
                )
            )
        )

        selected_roles = list(
            selected_roles_result.scalars().all()
        )

        if not selected_roles:
            return templates.TemplateResponse(
                request=request,
                name="admin/user_create.html",
                context={
                    **base_context,
                    "error": (
                        "Выберите хотя бы одну роль."
                    ),
                },
                status_code=400,
            )

        available_role_codes = {
            role.code
            for role in available_roles
        }

        selected_role_codes = {
            role.code
            for role in selected_roles
        }

        if not selected_role_codes.issubset(
            available_role_codes
        ):
            return templates.TemplateResponse(
                request=request,
                name="admin/user_create.html",
                context={
                    **base_context,
                    "error": (
                        "Вы пытаетесь назначить "
                        "роль, которую не имеете "
                        "права назначать."
                    ),
                },
                status_code=403,
            )

        role_error = (
            await validate_new_user_roles(
                db,
                actor,
                selected_roles,
            )
        )

        if role_error:
            return templates.TemplateResponse(
                request=request,
                name="admin/user_create.html",
                context={
                    **base_context,
                    "error": role_error,
                },
                status_code=403,
            )

        department_required = (
            roles_require_department(
                selected_roles
            )
        )

        department, department_error = (
            await validate_department(
                db,
                parsed_department_id,
                department_required,
            )
        )

        if department_error:
            return templates.TemplateResponse(
                request=request,
                name="admin/user_create.html",
                context={
                    **base_context,
                    "error": department_error,
                },
                status_code=400,
            )

        if department is not None:
            await ensure_scoped_access(
                db,
                actor,
                "users.invite",
                target_department_id=(
                    department.id
                ),
            )

        user = User(
            fio=fio,
            email=email,
            username=None,
            password_hash=None,
            department_id=(
                department.id
                if department
                else None
            ),
            status="invited",
            is_active=True,
        )

        db.add(
            user
        )

        await db.flush()

        for role in selected_roles:
            db.add(
                UserRole(
                    user_id=user.id,
                    role_id=role.id,
                )
            )

        invite, raw_token = (
            await invite_service.create_invite(
                db=db,
                user_id=user.id,
            )
        )

        await audit_service.write(
            db,
            action="users.invite",
            actor_user_id=actor.id,
            target_user_id=user.id,
            entity_type="user",
            entity_id=user.id,
            before_data=None,
            after_data=(
                build_user_audit_state(
                    user,
                    selected_role_codes,
                )
            ),
            request=request,
        )

        await db.commit()

        invite_url = (
            f"{settings.APP_BASE_URL}"
            f"/invite/{raw_token}"
        )

        email_sent = False
        email_error = None

        try:
            await email_service.send_invitation(
                to_email=user.email,
                fio=user.fio,
                invite_url=invite_url,
            )

            email_sent = True

        except EmailServiceError:
            email_error = (
                "Пользователь создан, "
                "но письмо отправить не удалось."
            )

    return templates.TemplateResponse(
        request=request,
        name="admin/user_create.html",
        context={
            "admin": actor,
            "roles": available_roles,
            "departments": departments,
            "error": None,
            "invite_url": invite_url,
            "created_user": user,
            "invite": invite,
            "email_sent": email_sent,
            "email_error": email_error,
        },
    )


@router.get(
    "/users/{user_id}/edit",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def user_edit_page(
    request: Request,
    user_id: int,
    actor: User = Depends(
        require_permission(
            "users.edit"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        user = await get_user_by_id(
            db,
            user_id,
        )

        if user is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Пользователь не найден.",
            )

        await ensure_scoped_access(
            db,
            actor,
            "users.edit",
            target_user_id=user.id,
        )

        all_roles = await get_all_roles(
            db
        )

        actor_role_codes = (
            await get_role_codes(
                db,
                actor.id,
            )
        )

        can_manage_roles = (
            await actor_can_manage_roles(
                db,
                actor,
            )
        )

        if "director" in actor_role_codes:
            roles = all_roles

        elif can_manage_roles:
            current_role_codes = (
                await get_role_codes(
                    db,
                    user.id,
                )
            )

            roles = [
                role
                for role in all_roles
                if (
                    role.code
                    not in PROTECTED_ROLE_CODES
                    or role.code
                    in current_role_codes
                )
            ]

        else:
            roles = await get_user_roles(
                db,
                user.id,
            )

        selected_role_ids = (
            await get_user_role_ids(
                db,
                user.id,
            )
        )

        departments = (
            await get_edit_departments_for_actor(
                db,
                actor,
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="admin/user_edit.html",
        context={
            "admin": actor,
            "edited_user": user,
            "roles": roles,
            "departments": departments,
            "selected_role_ids": (
                selected_role_ids
            ),
            "error": None,
            "action_success": None,
            "action_error": None,
            "invite_url": None,
        },
    )


@router.post(
    "/users/{user_id}/edit",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def user_edit(
    request: Request,
    user_id: int,
    fio: str = Form(...),
    email: str = Form(...),
    roles: list[str] = Form(...),
    department_id: str = Form(""),
    account_status: str = Form(...),
    actor: User = Depends(
        require_permission(
            "users.edit"
        )
    ),
):
    fio = fio.strip()
    email = email.strip().lower()

    parsed_department_id = (
        parse_department_id(
            department_id
        )
    )

    async with AsyncSessionLocal() as db:
        user = await get_user_by_id(
            db,
            user_id,
        )

        if user is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Пользователь не найден.",
            )

        await ensure_scoped_access(
            db,
            actor,
            "users.edit",
            target_user_id=user.id,
        )

        current_role_codes = (
            await get_role_codes(
                db,
                user.id,
            )
        )

        before_data = build_user_audit_state(
            user,
            current_role_codes,
        )

        all_roles = await get_all_roles(
            db
        )

        actor_role_codes = (
            await get_role_codes(
                db,
                actor.id,
            )
        )

        can_manage_roles = (
            await actor_can_manage_roles(
                db,
                actor,
            )
        )

        if "director" in actor_role_codes:
            visible_roles = all_roles

        elif can_manage_roles:
            visible_roles = [
                role
                for role in all_roles
                if (
                    role.code
                    not in PROTECTED_ROLE_CODES
                    or role.code
                    in current_role_codes
                )
            ]

        else:
            visible_roles = await get_user_roles(
                db,
                user.id,
            )

        departments = (
            await get_edit_departments_for_actor(
                db,
                actor,
            )
        )

        async def render_edit_error(
            message: str,
            status_code_value: int = 400,
        ):
            selected_role_ids = (
                await get_user_role_ids(
                    db,
                    user.id,
                )
            )

            return templates.TemplateResponse(
                request=request,
                name="admin/user_edit.html",
                context={
                    "admin": actor,
                    "edited_user": user,
                    "roles": visible_roles,
                    "departments": departments,
                    "selected_role_ids": (
                        selected_role_ids
                    ),
                    "error": message,
                    "action_success": None,
                    "action_error": None,
                    "invite_url": None,
                },
                status_code=status_code_value,
            )

        if not fio or not email:
            return await render_edit_error(
                "Заполните ФИО и email."
            )

        if user.status == "invited":
            if account_status != "invited":
                return await render_edit_error(
                    "Статус приглашённого "
                    "пользователя изменяется "
                    "автоматически после активации."
                )

        else:
            allowed_statuses = {
                "active",
                "disabled",
                "dismissed",
            }

            if account_status not in allowed_statuses:
                return await render_edit_error(
                    "Недопустимый статус."
                )

        if (
            user.id == actor.id
            and account_status
            in {
                "disabled",
                "dismissed",
            }
        ):
            return await render_edit_error(
                "Нельзя отключить или "
                "архивировать собственную "
                "учётную запись."
            )

        duplicate_result = await db.execute(
            select(User).where(
                User.email == email,
                User.id != user.id,
            )
        )

        duplicate_user = (
            duplicate_result.scalar_one_or_none()
        )

        if duplicate_user is not None:
            return await render_edit_error(
                "Этот email уже используется "
                "другим пользователем."
            )

        selected_roles_result = await db.execute(
            select(Role).where(
                Role.code.in_(
                    roles
                )
            )
        )

        selected_roles = list(
            selected_roles_result.scalars().all()
        )

        if not selected_roles:
            return await render_edit_error(
                "У пользователя должна быть "
                "хотя бы одна роль."
            )

        role_error = (
            await validate_role_assignment(
                db,
                actor,
                current_role_codes,
                selected_roles,
            )
        )

        if role_error:
            return await render_edit_error(
                role_error,
                403,
            )

        department_required = (
            roles_require_department(
                selected_roles
            )
        )

        department, department_error = (
            await validate_department(
                db,
                parsed_department_id,
                department_required,
            )
        )

        if department_error:
            return await render_edit_error(
                department_error
            )

        if department is not None:
            department_allowed = (
                await permission_service
                .can_access(
                    db=db,
                    user_id=actor.id,
                    permission_code="users.edit",
                    target_department_id=(
                        department.id
                    ),
                )
            )

            if not department_allowed:
                return await render_edit_error(
                    "Вы не можете переместить "
                    "пользователя в этот отдел.",
                    403,
                )

        selected_role_codes = {
            role.code
            for role in selected_roles
        }

        user.fio = fio
        user.email = email
        user.department_id = (
            department.id
            if department
            else None
        )

        if user.status != "invited":
            user.status = account_status

        user.is_active = (
            user.status
            in {
                "active",
                "invited",
            }
        )

        existing_user_roles_result = (
            await db.execute(
                select(UserRole).where(
                    UserRole.user_id == user.id
                )
            )
        )

        existing_user_roles = list(
            existing_user_roles_result
            .scalars()
            .all()
        )

        for user_role in existing_user_roles:
            await db.delete(
                user_role
            )

        await db.flush()

        for role in selected_roles:
            db.add(
                UserRole(
                    user_id=user.id,
                    role_id=role.id,
                )
            )

        after_data = build_user_audit_state(
            user,
            selected_role_codes,
        )

        await audit_service.write(
            db,
            action="users.edit",
            actor_user_id=actor.id,
            target_user_id=user.id,
            entity_type="user",
            entity_id=user.id,
            before_data=before_data,
            after_data=after_data,
            request=request,
        )

        await db.commit()

    return RedirectResponse(
        url="/admin/users",
        status_code=303,
    )


@router.post(
    "/users/{user_id}/resend-invite",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def resend_invite(
    request: Request,
    user_id: int,
    actor: User = Depends(
        require_permission(
            "users.invite"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        user = await get_user_by_id(
            db,
            user_id,
        )

        if user is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Пользователь не найден.",
            )

        await ensure_scoped_access(
            db,
            actor,
            "users.invite",
            target_user_id=user.id,
        )

        if user.status != "invited":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Повторное приглашение можно "
                    "отправить только пользователю "
                    "со статусом «Приглашён»."
                ),
            )

        if user.username is not None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Учётная запись уже была "
                    "активирована."
                ),
            )

        await db.execute(
            delete(Invite).where(
                Invite.user_id == user.id
            )
        )

        invite, raw_token = (
            await invite_service.create_invite(
                db=db,
                user_id=user.id,
            )
        )

        await audit_service.write(
            db,
            action="users.invite.resend",
            actor_user_id=actor.id,
            target_user_id=user.id,
            entity_type="user",
            entity_id=user.id,
            before_data=None,
            after_data={
                "email": user.email,
            },
            request=request,
        )

        await db.commit()

        invite_url = (
            f"{settings.APP_BASE_URL}"
            f"/invite/{raw_token}"
        )

        email_sent = False

        try:
            await email_service.send_invitation(
                to_email=user.email,
                fio=user.fio,
                invite_url=invite_url,
            )

            email_sent = True

        except EmailServiceError:
            email_sent = False

        actor_role_codes = (
            await get_role_codes(
                db,
                actor.id,
            )
        )

        can_manage_roles = (
            await actor_can_manage_roles(
                db,
                actor,
            )
        )

        current_role_codes = (
            await get_role_codes(
                db,
                user.id,
            )
        )

        all_roles = await get_all_roles(
            db
        )

        if "director" in actor_role_codes:
            roles = all_roles

        elif can_manage_roles:
            roles = [
                role
                for role in all_roles
                if (
                    role.code
                    not in PROTECTED_ROLE_CODES
                    or role.code
                    in current_role_codes
                )
            ]

        else:
            roles = await get_user_roles(
                db,
                user.id,
            )

        departments = (
            await get_edit_departments_for_actor(
                db,
                actor,
            )
        )

        selected_role_ids = (
            await get_user_role_ids(
                db,
                user.id,
            )
        )

    if email_sent:
        action_success = (
            "Новое приглашение отправлено на "
            f"{user.email}."
        )

        action_error = None
        fallback_invite_url = None

    else:
        action_success = None

        action_error = (
            "Новое приглашение создано, "
            "но письмо отправить не удалось."
        )

        fallback_invite_url = invite_url

    return templates.TemplateResponse(
        request=request,
        name="admin/user_edit.html",
        context={
            "admin": actor,
            "edited_user": user,
            "roles": roles,
            "departments": departments,
            "selected_role_ids": (
                selected_role_ids
            ),
            "error": None,
            "action_success": action_success,
            "action_error": action_error,
            "invite_url": fallback_invite_url,
        },
    )


@router.post(
    "/users/{user_id}/cancel-invite",
    include_in_schema=False,
)
async def cancel_invite(
    request: Request,
    user_id: int,
    actor: User = Depends(
        require_permission(
            "users.invite"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        user = await get_user_by_id(
            db,
            user_id,
        )

        if user is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Пользователь не найден.",
            )

        await ensure_scoped_access(
            db,
            actor,
            "users.invite",
            target_user_id=user.id,
        )

        if user.status != "invited":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Отменить можно только "
                    "неактивированное приглашение."
                ),
            )

        if user.username is not None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Учётная запись уже была "
                    "активирована и не может быть "
                    "удалена как приглашение."
                ),
            )

        if user.id == actor.id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Нельзя удалить собственную "
                    "учётную запись."
                ),
            )

        role_codes = await get_role_codes(
            db,
            user.id,
        )

        before_data = (
            build_user_audit_state(
                user,
                role_codes,
            )
        )

        await audit_service.write(
            db,
            action="users.invite.cancel",
            actor_user_id=actor.id,
            target_user_id=user.id,
            entity_type="user",
            entity_id=user.id,
            before_data=before_data,
            after_data=None,
            request=request,
        )

        await db.execute(
            delete(Session).where(
                Session.user_id == user.id
            )
        )

        await db.execute(
            delete(Invite).where(
                Invite.user_id == user.id
            )
        )

        await db.execute(
            delete(UserRole).where(
                UserRole.user_id == user.id
            )
        )

        await db.delete(
            user
        )

        await db.commit()

    return RedirectResponse(
        url="/admin/users?view=invited",
        status_code=303,
    )


# =========================================================
# AUDIT
# =========================================================


@router.get(
    "/audit",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def audit_page(
    request: Request,
    action: str = "",
    actor: str = "",
    target: str = "",
    page: int = 1,
    current_user: User = Depends(
        require_permission(
            "audit.view"
        )
    ),
):
    action = action.strip()
    actor = actor.strip()
    target = target.strip()

    if page < 1:
        page = 1

    async with AsyncSessionLocal() as db:
        conditions = []

        if action:
            conditions.append(
                AuditLog.action == action
            )

        if actor:
            if actor.isdigit():
                conditions.append(
                    AuditLog.actor_user_id
                    == int(actor)
                )

            else:
                actor_ids_query = (
                    select(User.id)
                    .where(
                        User.fio.ilike(
                            f"%{actor}%"
                        )
                    )
                )

                conditions.append(
                    AuditLog.actor_user_id.in_(
                        actor_ids_query
                    )
                )

        if target:
            if target.isdigit():
                conditions.append(
                    AuditLog.target_user_id
                    == int(target)
                )

            else:
                target_ids_query = (
                    select(User.id)
                    .where(
                        User.fio.ilike(
                            f"%{target}%"
                        )
                    )
                )

                conditions.append(
                    AuditLog.target_user_id.in_(
                        target_ids_query
                    )
                )

        count_query = select(
            func.count(
                AuditLog.id
            )
        )

        if conditions:
            count_query = (
                count_query.where(
                    *conditions
                )
            )

        count_result = await db.execute(
            count_query
        )

        total_count = (
            count_result.scalar_one()
        )

        total_pages = max(
            1,
            math.ceil(
                total_count
                / AUDIT_PAGE_SIZE
            ),
        )

        if page > total_pages:
            page = total_pages

        audit_query = (
            select(AuditLog)
            .order_by(
                AuditLog.id.desc()
            )
            .offset(
                (page - 1)
                * AUDIT_PAGE_SIZE
            )
            .limit(
                AUDIT_PAGE_SIZE
            )
        )

        if conditions:
            audit_query = (
                audit_query.where(
                    *conditions
                )
            )

        audit_result = await db.execute(
            audit_query
        )

        logs = list(
            audit_result
            .scalars()
            .all()
        )

        user_ids: set[int] = set()

        for log in logs:
            if log.actor_user_id is not None:
                user_ids.add(
                    log.actor_user_id
                )

            if log.target_user_id is not None:
                user_ids.add(
                    log.target_user_id
                )

        users_by_id = {}

        if user_ids:
            users_result = await db.execute(
                select(User).where(
                    User.id.in_(
                        user_ids
                    )
                )
            )

            users = list(
                users_result
                .scalars()
                .all()
            )

            users_by_id = {
                user.id: user
                for user in users
            }

        action_codes_result = (
            await db.execute(
                select(
                    AuditLog.action
                )
                .distinct()
                .order_by(
                    AuditLog.action
                )
            )
        )

        action_codes = list(
            action_codes_result
            .scalars()
            .all()
        )

        audit_items = []

        for log in logs:
            (
                before_lines,
                after_lines,
            ) = await build_audit_diff(
                db,
                log.before_data,
                log.after_data,
            )

            audit_items.append(
                {
                    "log": log,
                    "actor": (
                        users_by_id.get(
                            log.actor_user_id
                        )
                        if log.actor_user_id
                        is not None
                        else None
                    ),
                    "target": (
                        users_by_id.get(
                            log.target_user_id
                        )
                        if log.target_user_id
                        is not None
                        else None
                    ),
                    "before_lines": (
                        before_lines
                    ),
                    "after_lines": (
                        after_lines
                    ),
                }
            )

    def make_page_url(
        target_page: int,
    ) -> str:
        params = {
            "page": target_page,
        }

        if action:
            params["action"] = action

        if actor:
            params["actor"] = actor

        if target:
            params["target"] = target

        return (
            "/admin/audit?"
            + urlencode(params)
        )

    previous_page_url = None
    next_page_url = None

    if page > 1:
        previous_page_url = (
            make_page_url(
                page - 1
            )
        )

    if page < total_pages:
        next_page_url = (
            make_page_url(
                page + 1
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="admin/audit.html",
        context={
            "admin": current_user,
            "audit_items": audit_items,
            "action_codes": action_codes,
            "current_action": action,
            "current_actor": actor,
            "current_target": target,
            "total_count": total_count,
            "page": page,
            "total_pages": total_pages,
            "previous_page_url": (
                previous_page_url
            ),
            "next_page_url": (
                next_page_url
            ),
        },
    )


# =========================================================
# DEPARTMENTS
# =========================================================


@router.get(
    "/departments",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def departments_page(
    request: Request,
    actor: User = Depends(
        require_permission(
            "departments.view"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        departments = (
            await get_departments_data(
                db
            )
        )

        can_manage_departments = (
            await permission_service
            .has_permission(
                db,
                actor.id,
                "departments.manage",
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="admin/departments.html",
        context={
            "admin": actor,
            "departments": departments,
            "error": None,
            "can_manage_departments": (
                can_manage_departments
            ),
        },
    )


@router.post(
    "/departments/new",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def department_create(
    request: Request,
    name: str = Form(...),
    actor: User = Depends(
        require_permission(
            "departments.manage"
        )
    ),
):
    name = name.strip()

    async with AsyncSessionLocal() as db:
        if not name:
            departments = (
                await get_departments_data(
                    db
                )
            )

            return templates.TemplateResponse(
                request=request,
                name="admin/departments.html",
                context={
                    "admin": actor,
                    "departments": departments,
                    "error": (
                        "Укажите название отдела."
                    ),
                    "can_manage_departments": True,
                },
                status_code=400,
            )

        duplicate_result = await db.execute(
            select(Department).where(
                func.lower(
                    Department.name
                )
                == name.lower()
            )
        )

        duplicate = (
            duplicate_result.scalar_one_or_none()
        )

        if duplicate is not None:
            departments = (
                await get_departments_data(
                    db
                )
            )

            return templates.TemplateResponse(
                request=request,
                name="admin/departments.html",
                context={
                    "admin": actor,
                    "departments": departments,
                    "error": (
                        "Отдел с таким названием "
                        "уже существует."
                    ),
                    "can_manage_departments": True,
                },
                status_code=400,
            )

        department = Department(
            name=name,
            is_active=True,
        )

        db.add(
            department
        )

        await db.flush()

        await audit_service.write(
            db,
            action="departments.create",
            actor_user_id=actor.id,
            entity_type="department",
            entity_id=department.id,
            before_data=None,
            after_data={
                "name": department.name,
                "is_active": (
                    department.is_active
                ),
            },
            request=request,
        )

        await db.commit()

    return RedirectResponse(
        url="/admin/departments",
        status_code=303,
    )


@router.post(
    "/departments/{department_id}/rename",
    include_in_schema=False,
)
async def department_rename(
    request: Request,
    department_id: int,
    name: str = Form(...),
    actor: User = Depends(
        require_permission(
            "departments.manage"
        )
    ),
):
    name = name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail=(
                "Название отдела не может "
                "быть пустым."
            ),
        )

    async with AsyncSessionLocal() as db:
        department = (
            await get_department_by_id(
                db,
                department_id,
            )
        )

        if department is None:
            raise HTTPException(
                status_code=404,
                detail="Отдел не найден.",
            )

        duplicate_result = await db.execute(
            select(Department).where(
                func.lower(
                    Department.name
                )
                == name.lower(),
                Department.id
                != department.id,
            )
        )

        duplicate = (
            duplicate_result.scalar_one_or_none()
        )

        if duplicate is not None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Отдел с таким названием "
                    "уже существует."
                ),
            )

        old_name = department.name

        department.name = name

        await audit_service.write(
            db,
            action="departments.rename",
            actor_user_id=actor.id,
            entity_type="department",
            entity_id=department.id,
            before_data={
                "name": old_name,
            },
            after_data={
                "name": department.name,
            },
            request=request,
        )

        await db.commit()

    return RedirectResponse(
        url="/admin/departments",
        status_code=303,
    )


@router.post(
    "/departments/{department_id}/toggle",
    include_in_schema=False,
)
async def department_toggle(
    request: Request,
    department_id: int,
    actor: User = Depends(
        require_permission(
            "departments.manage"
        )
    ),
):
    async with AsyncSessionLocal() as db:
        department = (
            await get_department_by_id(
                db,
                department_id,
            )
        )

        if department is None:
            raise HTTPException(
                status_code=404,
                detail="Отдел не найден.",
            )

        old_is_active = (
            department.is_active
        )

        if department.is_active:
            users_result = await db.execute(
                select(
                    func.count(User.id)
                ).where(
                    User.department_id
                    == department.id,
                    User.status.in_(
                        [
                            "active",
                            "invited",
                        ]
                    ),
                )
            )

            users_count = (
                users_result.scalar_one()
            )

            if users_count > 0:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Нельзя отключить отдел, "
                        "пока в нём есть активные "
                        "или приглашённые пользователи."
                    ),
                )

            department.is_active = False

            action = (
                "departments.disable"
            )

        else:
            department.is_active = True

            action = (
                "departments.enable"
            )

        await audit_service.write(
            db,
            action=action,
            actor_user_id=actor.id,
            entity_type="department",
            entity_id=department.id,
            before_data={
                "name": department.name,
                "is_active": old_is_active,
            },
            after_data={
                "name": department.name,
                "is_active": (
                    department.is_active
                ),
            },
            request=request,
        )

        await db.commit()

    return RedirectResponse(
        url="/admin/departments",
        status_code=303,
    )