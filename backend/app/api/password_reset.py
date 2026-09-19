import logging

logger = logging.getLogger(__name__)

from datetime import (
    datetime,
    timezone,
)

from fastapi import (
    APIRouter,
    Form,
    Request,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import (
    delete,
    select,
)

from backend.app.core.config import (
    TEMPLATES_DIR,
    settings,
)
from backend.app.core.database import (
    AsyncSessionLocal,
)
from backend.app.core.security import (
    hash_password,
    hash_token,
)
from backend.app.models.password_reset_token import (
    PasswordResetToken,
)
from backend.app.models.session import Session
from backend.app.models.user import User
from backend.app.services.email_service import (
    EmailServiceError,
    email_service,
)
from backend.app.services.password_reset_service import (
    password_reset_service,
)


router = APIRouter(
    tags=["password-reset"],
)

templates = Jinja2Templates(
    directory=TEMPLATES_DIR
)


GENERIC_RESET_MESSAGE = (
    "Если учётная запись с таким email существует, "
    "ссылка для восстановления отправлена на почту."
)


@router.get(
    "/forgot-password",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def forgot_password_page(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="forgot_password.html",
        context={
            "error": None,
            "success": None,
        },
    )


@router.post(
    "/forgot-password",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def forgot_password(
    request: Request,
    email: str = Form(...),
):
    email = (
        email
        .strip()
        .lower()
    )

    if not email:
        return templates.TemplateResponse(
            request=request,
            name="forgot_password.html",
            context={
                "error": "Укажите email.",
                "success": None,
            },
            status_code=400,
        )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(
                User.email == email
            )
        )

        user = result.scalar_one_or_none()

        if (
            user is not None
            and user.status == "active"
            and user.is_active
            and user.password_hash
        ):
            _, raw_token = (
                await password_reset_service
                .create_reset_token(
                    db=db,
                    user_id=user.id,
                )
            )

            await db.commit()

            reset_url = (
                f"{settings.APP_BASE_URL}"
                f"/reset-password/{raw_token}"
            )

            try:
                await email_service.send_password_reset(
                    to_email=user.email,
                    fio=user.fio,
                    reset_url=reset_url,
                )


            except EmailServiceError:
                logger.exception(
                    "Не удалось отправить письмо восстановления пароля."
                )
                pass

    return templates.TemplateResponse(
        request=request,
        name="forgot_password.html",
        context={
            "error": None,
            "success": GENERIC_RESET_MESSAGE,
        },
    )


async def get_valid_reset_token(
    token: str,
):
    token_hash = hash_token(
        token
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                PasswordResetToken
            ).where(
                PasswordResetToken.token_hash
                == token_hash
            )
        )

        reset_token = (
            result.scalar_one_or_none()
        )

        if reset_token is None:
            return (
                None,
                None,
                "Ссылка восстановления недействительна.",
            )

        if reset_token.used_at is not None:
            return (
                None,
                None,
                "Ссылка восстановления уже была использована.",
            )

        now = datetime.now(
            timezone.utc
        )

        if reset_token.expires_at < now:
            return (
                None,
                None,
                "Срок действия ссылки восстановления истёк.",
            )

        user_result = await db.execute(
            select(User).where(
                User.id
                == reset_token.user_id
            )
        )

        user = (
            user_result.scalar_one_or_none()
        )

        if user is None:
            return (
                None,
                None,
                "Учётная запись не найдена.",
            )

        if (
            user.status != "active"
            or not user.is_active
        ):
            return (
                None,
                None,
                "Учётная запись недоступна.",
            )

        return (
            reset_token,
            user,
            None,
        )


@router.get(
    "/reset-password/{token}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def reset_password_page(
    request: Request,
    token: str,
):
    _, user, error = (
        await get_valid_reset_token(
            token
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="reset_password.html",
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
    "/reset-password/{token}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def reset_password(
    request: Request,
    token: str,
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    _, user, error = (
        await get_valid_reset_token(
            token
        )
    )

    if error:
        return templates.TemplateResponse(
            request=request,
            name="reset_password.html",
            context={
                "token": token,
                "user": user,
                "error": error,
                "success": False,
            },
            status_code=400,
        )

    if len(password) < 10:
        return templates.TemplateResponse(
            request=request,
            name="reset_password.html",
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
            name="reset_password.html",
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
        reset_result = await db.execute(
            select(
                PasswordResetToken
            )
            .where(
                PasswordResetToken.token_hash
                == token_hash
            )
            .with_for_update()
        )

        db_reset_token = (
            reset_result.scalar_one_or_none()
        )

        if db_reset_token is None:
            return templates.TemplateResponse(
                request=request,
                name="reset_password.html",
                context={
                    "token": token,
                    "user": user,
                    "error": (
                        "Ссылка восстановления "
                        "недействительна."
                    ),
                    "success": False,
                },
                status_code=400,
            )

        now = datetime.now(
            timezone.utc
        )

        if (
            db_reset_token.used_at is not None
            or db_reset_token.expires_at < now
        ):
            return templates.TemplateResponse(
                request=request,
                name="reset_password.html",
                context={
                    "token": token,
                    "user": user,
                    "error": (
                        "Ссылка восстановления "
                        "больше недействительна."
                    ),
                    "success": False,
                },
                status_code=400,
            )

        user_result = await db.execute(
            select(User)
            .where(
                User.id
                == db_reset_token.user_id
            )
            .with_for_update()
        )

        db_user = (
            user_result.scalar_one_or_none()
        )

        if (
            db_user is None
            or db_user.status != "active"
            or not db_user.is_active
        ):
            return templates.TemplateResponse(
                request=request,
                name="reset_password.html",
                context={
                    "token": token,
                    "user": user,
                    "error": (
                        "Учётная запись недоступна."
                    ),
                    "success": False,
                },
                status_code=400,
            )

        db_user.password_hash = (
            hash_password(
                password
            )
        )

        db_reset_token.used_at = now

        # После успешной смены пароля
        # отзываем абсолютно все старые сессии.
        await db.execute(
            delete(Session).where(
                Session.user_id
                == db_user.id
            )
        )

        # Если каким-то образом остались другие
        # reset-токены этого пользователя,
        # они также больше не должны работать.
        await db.execute(
            delete(
                PasswordResetToken
            ).where(
                PasswordResetToken.user_id
                == db_user.id,
                PasswordResetToken.id
                != db_reset_token.id,
            )
        )

        await db.commit()

    return templates.TemplateResponse(
        request=request,
        name="reset_password.html",
        context={
            "token": token,
            "user": user,
            "error": None,
            "success": True,
        },
    )