from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.core.auth import get_current_user
from backend.app.models.user import User
from backend.app.services.chat_service import (
    chat_service,
)


router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
)


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
    )


class ActionChoice(BaseModel):
    label: str
    value: str
    href: str | None = None


class ChatAction(BaseModel):
    type: Literal[
        "call",
        "email",
        "choose_person",
        "choose_phone",
    ]

    intent: Literal[
        "call",
        "email",
    ] | None = None

    label: str | None = None
    value: str | None = None
    href: str | None = None

    choices: list[ActionChoice] = Field(
        default_factory=list
    )


class ChatResponse(BaseModel):
    answer: str
    action: ChatAction | None = None


@router.post(
    "",
    response_model=ChatResponse,
)
async def send_message(
    payload: ChatRequest,
    user: User = Depends(get_current_user),
) -> ChatResponse:
    result = await chat_service.process_message(
        message=payload.message,
        user_id=user.id,
    )

    return ChatResponse(
        answer=result.answer,
        action=result.action,
    )