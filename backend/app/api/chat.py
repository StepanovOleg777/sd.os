from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.services.chat_service import chat_service


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


class ChatResponse(BaseModel):
    answer: str


@router.post(
    "",
    response_model=ChatResponse,
)
async def send_message(payload: ChatRequest) -> ChatResponse:
    answer = await chat_service.process_message(payload.message)

    return ChatResponse(
        answer=answer,
    )