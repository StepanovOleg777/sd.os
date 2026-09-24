import asyncio
from contextlib import asynccontextmanager

from redis.exceptions import LockError

from backend.app.core.redis import redis_client


LOCK_TIMEOUT_SECONDS = 120
BLOCKING_TIMEOUT_SECONDS = 120


@asynccontextmanager
async def conversation_lock(
    conversation_id: int,
):
    lock = redis_client.lock(
        name=f"ai:conversation:{conversation_id}:lock",
        timeout=LOCK_TIMEOUT_SECONDS,
        blocking_timeout=BLOCKING_TIMEOUT_SECONDS,
    )

    acquired = await lock.acquire()

    if not acquired:
        raise TimeoutError(
            "Не удалось получить блокировку AI-диалога."
        )

    try:
        yield

    finally:
        try:
            await lock.release()

        except LockError:
            pass

        except asyncio.CancelledError:
            raise