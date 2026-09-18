from datetime import datetime, timezone

from fastapi import Cookie, HTTPException, status
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.core.security import hash_token
from backend.app.models.session import Session
from backend.app.models.user import User


SESSION_COOKIE_NAME = "sdos_session"


async def get_current_user(
    sdos_session: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> User:
    if not sdos_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не авторизован.",
        )

    token_hash = hash_token(
        sdos_session
    )

    now = datetime.now(
        timezone.utc
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Session).where(
                Session.token_hash == token_hash
            )
        )

        session = result.scalar_one_or_none()

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Сессия не найдена.",
            )

        if session.expires_at < now:
            await db.delete(
                session
            )

            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Сессия истекла.",
            )

        user_result = await db.execute(
            select(User).where(
                User.id == session.user_id
            )
        )

        user = user_result.scalar_one_or_none()

        if (
            user is None
            or not user.is_active
            or user.status != "active"
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Учётная запись недоступна.",
            )

        session.last_seen_at = now

        await db.commit()

        return user


async def get_optional_current_user(
    sdos_session: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> User | None:
    if not sdos_session:
        return None

    token_hash = hash_token(
        sdos_session
    )

    now = datetime.now(
        timezone.utc
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Session).where(
                Session.token_hash == token_hash
            )
        )

        session = result.scalar_one_or_none()

        if session is None:
            return None

        if session.expires_at < now:
            await db.delete(
                session
            )

            await db.commit()

            return None

        user_result = await db.execute(
            select(User).where(
                User.id == session.user_id
            )
        )

        user = user_result.scalar_one_or_none()

        if (
            user is None
            or not user.is_active
            or user.status != "active"
        ):
            return None

        session.last_seen_at = now

        await db.commit()

        return user