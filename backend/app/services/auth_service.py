from datetime import (
    datetime,
    timedelta,
    timezone,
)

from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.core.security import (
    generate_invite_token,
    hash_token,
    verify_password,
)
from backend.app.models.session import Session
from backend.app.models.user import User


SESSION_TTL_HOURS = 24


class AuthError(Exception):
    pass


class AuthService:
    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> tuple[User, str]:

        normalized_username = (
            username
            .strip()
            .lower()
        )

        if not normalized_username:
            raise AuthError(
                "Неверный логин или пароль."
            )

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(
                    User.username
                    == normalized_username
                )
            )

            user = result.scalar_one_or_none()

            if user is None:
                raise AuthError(
                    "Неверный логин или пароль."
                )

            if not user.is_active:
                raise AuthError(
                    "Учётная запись отключена."
                )

            if user.status != "active":
                raise AuthError(
                    "Учётная запись ещё не активирована."
                )

            if not user.password_hash:
                raise AuthError(
                    "Для пользователя не задан пароль."
                )

            if not verify_password(
                password,
                user.password_hash,
            ):
                raise AuthError(
                    "Неверный логин или пароль."
                )

            raw_token = (
                generate_invite_token()
            )

            token_hash = hash_token(
                raw_token
            )

            now = datetime.now(
                timezone.utc
            )

            session = Session(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=(
                    now
                    + timedelta(
                        hours=SESSION_TTL_HOURS
                    )
                ),
                created_at=now,
                last_seen_at=now,
            )

            user.last_login = now

            db.add(
                session
            )

            await db.commit()

            return (
                user,
                raw_token,
            )


auth_service = AuthService()