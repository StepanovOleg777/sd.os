from datetime import (
    datetime,
    timedelta,
    timezone,
)

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.security import (
    generate_invite_token,
    hash_token,
)
from backend.app.models.password_reset_token import (
    PasswordResetToken,
)


class PasswordResetService:
    async def create_reset_token(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> tuple[PasswordResetToken, str]:

        # Старые reset-токены этого пользователя
        # больше не должны работать.
        await db.execute(
            delete(
                PasswordResetToken
            ).where(
                PasswordResetToken.user_id
                == user_id
            )
        )

        raw_token = generate_invite_token()

        now = datetime.now(
            timezone.utc
        )

        reset_token = PasswordResetToken(
            user_id=user_id,
            token_hash=hash_token(
                raw_token
            ),
            expires_at=(
                now
                + timedelta(
                    minutes=(
                        settings.PASSWORD_RESET_TTL_MINUTES
                    )
                )
            ),
            used_at=None,
            created_at=now,
        )

        db.add(
            reset_token
        )

        await db.flush()

        return (
            reset_token,
            raw_token,
        )


password_reset_service = PasswordResetService()