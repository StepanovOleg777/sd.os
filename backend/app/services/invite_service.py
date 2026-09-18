from datetime import (
    datetime,
    timedelta,
    timezone,
)

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import (
    generate_invite_token,
    hash_token,
)
from backend.app.models.invite import Invite


INVITE_TTL_HOURS = 24


class InviteService:
    async def create_invite(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> tuple[Invite, str]:
        raw_token = generate_invite_token()

        now = datetime.now(
            timezone.utc
        )

        invite = Invite(
            user_id=user_id,
            token_hash=hash_token(
                raw_token
            ),
            expires_at=(
                now
                + timedelta(
                    hours=INVITE_TTL_HOURS
                )
            ),
            created_at=now,
            used_at=None,
        )

        db.add(invite)

        await db.flush()

        return (
            invite,
            raw_token,
        )


invite_service = InviteService()