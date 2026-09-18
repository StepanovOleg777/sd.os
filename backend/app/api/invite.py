from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from backend.app.core.config import TEMPLATES_DIR
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.security import (
    hash_password,
    hash_token,
)
from backend.app.models.invite import Invite
from backend.app.models.user import User


router = APIRouter(
    tags=["invite"],
)

templates = Jinja2Templates(
    directory=TEMPLATES_DIR
)


async def get_valid_invite(
    token: str,
):
    token_hash = hash_token(
        token
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Invite).where(
                Invite.token_hash == token_hash
            )
        )

        invite = result.scalar_one_or_none()

        if invite is None:
            return None, None, "Приглашение не найдено."

        if invite.used_at is not None:
            return (
                None,
                None,
                "Приглашение уже было использовано.",
            )

        now = datetime.now(
            timezone.utc
        )

        if invite.expires_at < now:
            return (
                None,
                None,
                "Срок действия приглашения истёк.",
            )

        user_result = await db.execute(
            select(User).where(
                User.id == invite.user_id
            )
        )

        user = user_result.scalar_one_or_none()

        if user is None:
            return (
                None,
                None,
                "Пользователь не найден.",
            )

        if user.status != "invited":
            return (
                None,
                None,
                "Учётная запись уже активирована "
                "или недоступна.",
            )

        return (
            invite,
            user,
            None,
        )


@router.get(
    "/invite/{token}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def invite_page(
    request: Request,
    token: str,
):
    invite, user, error = (
        await get_valid_invite(
            token
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="invite.html",
        context={
            "token": token,
            "user": user,
            "error": error,
            "success": False,
        },
        status_code=(
            400
            if error
            else 200
        ),
    )


@router.post(
    "/invite/{token}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def activate_invite(
    request: Request,
    token: str,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    username = (
        username
        .strip()
        .lower()
    )

    invite, user, error = (
        await get_valid_invite(
            token
        )
    )

    if error:
        return templates.TemplateResponse(
            request=request,
            name="invite.html",
            context={
                "token": token,
                "user": user,
                "error": error,
                "success": False,
            },
            status_code=400,
        )

    if len(username) < 3:
        return templates.TemplateResponse(
            request=request,
            name="invite.html",
            context={
                "token": token,
                "user": user,
                "error": (
                    "Логин должен содержать "
                    "минимум 3 символа."
                ),
                "success": False,
            },
            status_code=400,
        )

    if len(password) < 10:
        return templates.TemplateResponse(
            request=request,
            name="invite.html",
            context={
                "token": token,
                "user": user,
                "error": (
                    "Пароль должен содержать "
                    "минимум 10 символов."
                ),
                "success": False,
            },
            status_code=400,
        )

    if password != password_confirm:
        return templates.TemplateResponse(
            request=request,
            name="invite.html",
            context={
                "token": token,
                "user": user,
                "error": "Пароли не совпадают.",
                "success": False,
            },
            status_code=400,
        )

    token_hash = hash_token(
        token
    )

    async with AsyncSessionLocal() as db:
        username_result = await db.execute(
            select(User).where(
                User.username == username
            )
        )

        existing_user = (
            username_result.scalar_one_or_none()
        )

        if existing_user is not None:
            return templates.TemplateResponse(
                request=request,
                name="invite.html",
                context={
                    "token": token,
                    "user": user,
                    "error": (
                        "Такой логин уже занят."
                    ),
                    "success": False,
                },
                status_code=400,
            )

        invite_result = await db.execute(
            select(Invite).where(
                Invite.token_hash == token_hash
            )
        )

        db_invite = (
            invite_result.scalar_one_or_none()
        )

        if (
            db_invite is None
            or db_invite.used_at is not None
        ):
            return templates.TemplateResponse(
                request=request,
                name="invite.html",
                context={
                    "token": token,
                    "user": user,
                    "error": (
                        "Приглашение больше "
                        "недействительно."
                    ),
                    "success": False,
                },
                status_code=400,
            )

        now = datetime.now(
            timezone.utc
        )

        if db_invite.expires_at < now:
            return templates.TemplateResponse(
                request=request,
                name="invite.html",
                context={
                    "token": token,
                    "user": user,
                    "error": (
                        "Срок действия приглашения "
                        "истёк."
                    ),
                    "success": False,
                },
                status_code=400,
            )

        user_result = await db.execute(
            select(User).where(
                User.id == db_invite.user_id
            )
        )

        db_user = (
            user_result.scalar_one_or_none()
        )

        if (
            db_user is None
            or db_user.status != "invited"
        ):
            return templates.TemplateResponse(
                request=request,
                name="invite.html",
                context={
                    "token": token,
                    "user": user,
                    "error": (
                        "Учётная запись "
                        "недоступна для активации."
                    ),
                    "success": False,
                },
                status_code=400,
            )

        db_user.username = username
        db_user.password_hash = (
            hash_password(
                password
            )
        )
        db_user.status = "active"
        db_user.is_active = True

        db_invite.used_at = now

        await db.commit()

    return templates.TemplateResponse(
        request=request,
        name="invite.html",
        context={
            "token": token,
            "user": user,
            "error": None,
            "success": True,
        },
    )