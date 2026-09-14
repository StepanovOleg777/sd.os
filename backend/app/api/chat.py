from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

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
) -> ChatResponse:
    result = (
        await chat_service.process_message(
            payload.message
        )
    )

    return ChatResponse(
        answer=result.answer,
        action=result.action,
    )