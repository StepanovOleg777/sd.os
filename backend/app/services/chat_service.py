from dataclasses import dataclass
from typing import Any

from backend.app.services.openai_service import (
    openai_service,
)


@dataclass
class ChatServiceResult:
    answer: str
    action: dict[str, Any] | None = None


class ChatService:
    async def process_message(
        self,
        message: str,
        user_id: int,
    ) -> ChatServiceResult:

        message = message.strip()

        try:
            answer, action = (
                await openai_service.process(
                    message=message,
                    user_id=user_id,
                )
            )

        except Exception as exc:
            return ChatServiceResult(
                answer=(
                    "Ошибка обращения к ИИ: "
                    f"{exc}"
                ),
            )

        return ChatServiceResult(
            answer=answer,
            action=action,
        )


chat_service = ChatService()