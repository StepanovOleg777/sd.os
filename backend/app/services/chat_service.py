from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from backend.app.core.conversation_lock import (
    conversation_lock,
)
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.ai import (
    AIConversation,
    AIMessage,
)
from backend.app.services.openai_service import (
    openai_service,
)


@dataclass
class ChatServiceResult:
    answer: str
    conversation_public_id: UUID
    action: dict[str, Any] | None = None


class ChatService:
    async def process_message(
        self,
        message: str,
        user_id: int,
        conversation_public_id: UUID | None,
    ) -> ChatServiceResult:

        message = message.strip()

        async with AsyncSessionLocal() as db:
            conversation = None

            if conversation_public_id is not None:
                result = await db.execute(
                    select(AIConversation).where(
                        AIConversation.public_id
                        == conversation_public_id,
                        AIConversation.user_id
                        == user_id,
                        AIConversation.status
                        == "active",
                    )
                )

                conversation = (
                    result.scalar_one_or_none()
                )

                if conversation is None:
                    raise HTTPException(
                        status_code=404,
                        detail="AI-диалог не найден.",
                    )

            else:
                conversation = AIConversation(
                    user_id=user_id,
                    title=message[:255],
                    status="active",
                )

                db.add(conversation)

                await db.commit()

                await db.refresh(
                    conversation
                )

        async with conversation_lock(
            conversation.id
        ):
            async with AsyncSessionLocal() as db:
                user_message = AIMessage(
                    conversation_id=(
                        conversation.id
                    ),
                    role="user",
                    text=message,
                )

                db.add(user_message)

                await db.commit()

            try:
                answer, action = (
                    await openai_service.process(
                        message=message,
                        user_id=user_id,
                        conversation_id=(
                            conversation.id
                        ),
                    )
                )

            except Exception as exc:
                return ChatServiceResult(
                    answer=(
                        "Ошибка обращения к ИИ: "
                        f"{exc}"
                    ),
                    conversation_public_id=(
                        conversation.public_id
                    ),
                )

            async with AsyncSessionLocal() as db:
                assistant_message = AIMessage(
                    conversation_id=(
                        conversation.id
                    ),
                    role="assistant",
                    text=answer,
                )

                db.add(assistant_message)

                await db.commit()

        return ChatServiceResult(
            answer=answer,
            conversation_public_id=(
                conversation.public_id
            ),
            action=action,
        )


chat_service = ChatService()