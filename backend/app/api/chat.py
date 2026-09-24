from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.app.core.auth import get_current_user
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.ai import (
    AIConversation,
    AIMessage,
)
from backend.app.models.user import User
from backend.app.services.chat_service import (
    chat_service,
)


router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
)


# =========================================================
# CHAT MESSAGE
# =========================================================


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
    )

    conversation_id: UUID | None = None


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


class ConversationRenameRequest(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )


class ChatResponse(BaseModel):
    answer: str
    conversation_id: UUID
    action: ChatAction | None = None


# =========================================================
# CONVERSATIONS
# =========================================================


class ConversationListItem(BaseModel):
    conversation_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class ConversationMessage(BaseModel):
    id: int
    role: str
    text: str | None
    created_at: datetime


class ConversationHistoryResponse(BaseModel):
    conversation_id: UUID
    title: str | None
    messages: list[ConversationMessage]


# =========================================================
# SEND MESSAGE
# =========================================================


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
        conversation_public_id=(
            payload.conversation_id
        ),
    )

    return ChatResponse(
        answer=result.answer,
        conversation_id=(
            result.conversation_public_id
        ),
        action=result.action,
    )


# =========================================================
# LIST CONVERSATIONS
# =========================================================


@router.get(
    "/conversations",
    response_model=list[ConversationListItem],
)
async def list_conversations(
    user: User = Depends(get_current_user),
) -> list[ConversationListItem]:

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AIConversation)
            .where(
                AIConversation.user_id == user.id,
                AIConversation.status == "active",
            )
            .order_by(
                AIConversation.created_at.desc()
            )
        )

        conversations = (
            result.scalars().all()
        )

    return [
        ConversationListItem(
            conversation_id=(
                conversation.public_id
            ),
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
        for conversation in conversations
    ]


# =========================================================
# CONVERSATION HISTORY
# =========================================================

@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationListItem,
)
async def rename_conversation(
    conversation_id: UUID,
    payload: ConversationRenameRequest,
    user: User = Depends(get_current_user),
) -> ConversationListItem:

    title = payload.title.strip()

    if not title:
        raise HTTPException(
            status_code=422,
            detail="Название чата не может быть пустым.",
        )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AIConversation).where(
                AIConversation.public_id
                == conversation_id,
                AIConversation.user_id
                == user.id,
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

        conversation.title = title

        await db.commit()
        await db.refresh(conversation)

    return ConversationListItem(
        conversation_id=conversation.public_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse,
)
async def get_conversation_history(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
) -> ConversationHistoryResponse:

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AIConversation).where(
                AIConversation.public_id
                == conversation_id,
                AIConversation.user_id
                == user.id,
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

        result = await db.execute(
            select(AIMessage)
            .where(
                AIMessage.conversation_id
                == conversation.id
            )
            .order_by(
                AIMessage.id.asc()
            )
        )

        messages = result.scalars().all()

    return ConversationHistoryResponse(
        conversation_id=conversation.public_id,
        title=conversation.title,
        messages=[
            ConversationMessage(
                id=message.id,
                role=message.role,
                text=message.text,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=204,
)
async def delete_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
) -> None:

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AIConversation).where(
                AIConversation.public_id
                == conversation_id,
                AIConversation.user_id
                == user.id,
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

        conversation.status = "deleted"

        await db.commit()