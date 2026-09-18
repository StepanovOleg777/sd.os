from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from backend.app.core.config import TEMPLATES_DIR
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.permissions import require_admin
from backend.app.models.role import Role, UserRole
from backend.app.models.user import User
from backend.app.services.invite_service import invite_service


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


async def get_users_data(
    view: str,
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

        users = result.scalars().all()

        users_data = []

        for user in users:
            roles_result = await db.execute(
                select(Role)
                .join(
                    UserRole,
                    UserRole.role_id == Role.id,
                )
                .where(
                    UserRole.user_id == user.id
                )
                .order_by(
                    Role.name
                )
            )

            roles = list(
                roles_result.scalars().all()
            )

            users_data.append(
                {
                    "user": user,
                    "roles": roles,
                }
            )

        return users_data


@router.get(
    "/users",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def users_page(
    request: Request,
    view: str = "active",
    admin: User = Depends(require_admin),
):
    if view not in USER_VIEWS:
        view = "active"

    users = await get_users_data(
        view
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/users.html",
        context={
            "admin": admin,
            "users": users,
            "current_view": view,
            "views": USER_VIEWS,
        },
    )


@router.get(
    "/users/new",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def user_create_page(
    request: Request,
    admin: User = Depends(require_admin),
):
    async with AsyncSessionLocal() as db:
        roles = await get_all_roles(
            db
        )

    return templates.TemplateResponse(
        request=request,
        name="admin/user_create.html",
        context={
            "admin": admin,
            "roles": roles,
            "error": None,
            "invite_url": None,
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
    admin: User = Depends(require_admin),
):
    fio = fio.strip()
    email = email.strip().lower()

    async with AsyncSessionLocal() as db:
        all_roles = await get_all_roles(
            db
        )

        if not fio:
            return templates.TemplateResponse(
                request=request,
                name="admin/user_create.html",
                context={
                    "admin": admin,
                    "roles": all_roles,
                    "error": "Укажите ФИО.",
                    "invite_url": None,
                },
                status_code=400,
            )

        if not email:
            return templates.TemplateResponse(
                request=request,
                name="admin/user_create.html",
                context={
                    "admin": admin,
                    "roles": all_roles,
                    "error": "Укажите email.",
                    "invite_url": None,
                },
                status_code=400,
            )

        existing_result = await db.execute(
            select(User).where(
                User.email == email
            )
        )

        if (
            existing_result.scalar_one_or_none()
            is not None
        ):
            return templates.TemplateResponse(
                request=request,
                name="admin/user_create.html",
                context={
                    "admin": admin,
                    "roles": all_roles,
                    "error": (
                        "Пользователь с таким "
                        "email уже существует."
                    ),
                    "invite_url": None,
                },
                status_code=400,
            )

        selected_roles_result = await db.execute(
            select(Role).where(
                Role.code.in_(roles)
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
                    "admin": admin,
                    "roles": all_roles,
                    "error": (
                        "Выберите хотя бы одну роль."
                    ),
                    "invite_url": None,
                },
                status_code=400,
            )

        user = User(
            fio=fio,
            email=email,
            username=None,
            password_hash=None,
            status="invited",
            is_active=True,
        )

        db.add(user)

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

        await db.commit()

        invite_url = (
            f"{str(request.base_url).rstrip('/')}"
            f"/invite/{raw_token}"
        )

    return templates.TemplateResponse(
        request=request,
        name="admin/user_create.html",
        context={
            "admin": admin,
            "roles": all_roles,
            "error": None,
            "invite_url": invite_url,
            "created_user": user,
            "invite": invite,
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
    admin: User = Depends(require_admin),
):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(
                User.id == user_id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден.",
            )

        roles = await get_all_roles(
            db
        )

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
            "admin": admin,
            "edited_user": user,
            "roles": roles,
            "selected_role_ids": selected_role_ids,
            "error": None,
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
    account_status: str = Form(...),
    admin: User = Depends(require_admin),
):
    fio = fio.strip()
    email = email.strip().lower()

    allowed_statuses = {
        "invited",
        "active",
        "disabled",
        "dismissed",
    }

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(
                User.id == user_id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден.",
            )

        all_roles = await get_all_roles(
            db
        )

        if not fio or not email:
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
                    "admin": admin,
                    "edited_user": user,
                    "roles": all_roles,
                    "selected_role_ids": selected_role_ids,
                    "error": "Заполните ФИО и email.",
                },
                status_code=400,
            )

        if account_status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Недопустимый статус.",
            )

        if (
            user.id == admin.id
            and account_status
            in {
                "disabled",
                "dismissed",
            }
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
                    "admin": admin,
                    "edited_user": user,
                    "roles": all_roles,
                    "selected_role_ids": selected_role_ids,
                    "error": (
                        "Нельзя отключить или "
                        "архивировать собственную "
                        "учётную запись."
                    ),
                },
                status_code=400,
            )

        duplicate_result = await db.execute(
            select(User).where(
                User.email == email,
                User.id != user.id,
            )
        )

        if (
            duplicate_result.scalar_one_or_none()
            is not None
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
                    "admin": admin,
                    "edited_user": user,
                    "roles": all_roles,
                    "selected_role_ids": selected_role_ids,
                    "error": (
                        "Этот email уже используется "
                        "другим пользователем."
                    ),
                },
                status_code=400,
            )

        selected_roles_result = await db.execute(
            select(Role).where(
                Role.code.in_(roles)
            )
        )

        selected_roles = list(
            selected_roles_result.scalars().all()
        )

        if not selected_roles:
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
                    "admin": admin,
                    "edited_user": user,
                    "roles": all_roles,
                    "selected_role_ids": selected_role_ids,
                    "error": (
                        "У пользователя должна быть "
                        "хотя бы одна роль."
                    ),
                },
                status_code=400,
            )

        user.fio = fio
        user.email = email
        user.status = account_status

        user.is_active = (
            account_status
            in {
                "active",
                "invited",
            }
        )

        current_roles_result = await db.execute(
            select(UserRole).where(
                UserRole.user_id == user.id
            )
        )

        current_roles = (
            current_roles_result.scalars().all()
        )

        for user_role in current_roles:
            await db.delete(
                user_role
            )

        # Сначала реально удаляем старые связи ролей из БД.
        await db.flush()

        for role in selected_roles:
            db.add(
                UserRole(
                    user_id=user.id,
                    role_id=role.id,
                )
            )

        await db.commit()

    return RedirectResponse(
        url="/admin/users",
        status_code=303,
    )

