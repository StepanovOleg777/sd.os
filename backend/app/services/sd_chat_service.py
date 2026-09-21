from datetime import datetime

from sqlalchemy import (
    and_,
    func,
    select,
)
from sqlalchemy.orm import aliased

from backend.app.models.sd_chat import (
    ChatConversation,
    ChatMessage,
    ChatParticipant,
)
from backend.app.models.user import User


class SDChatService:

    async def get_direct_conversation(
        self,
        db,
        user_id: int,
        other_user_id: int,
    ) -> ChatConversation | None:
        participant_a = aliased(
            ChatParticipant
        )

        participant_b = aliased(
            ChatParticipant
        )

        result = await db.execute(
            select(
                ChatConversation
            )
            .join(
                participant_a,
                and_(
                    participant_a.conversation_id
                    == ChatConversation.id,
                    participant_a.user_id
                    == user_id,
                ),
            )
            .join(
                participant_b,
                and_(
                    participant_b.conversation_id
                    == ChatConversation.id,
                    participant_b.user_id
                    == other_user_id,
                ),
            )
            .where(
                ChatConversation.conversation_type
                == "direct"
            )
        )

        conversations = list(
            result.scalars().all()
        )

        for conversation in conversations:
            participant_count_result = (
                await db.execute(
                    select(
                        func.count(
                            ChatParticipant.id
                        )
                    )
                    .where(
                        ChatParticipant.conversation_id
                        == conversation.id
                    )
                )
            )

            participant_count = (
                participant_count_result
                .scalar_one()
            )

            if participant_count == 2:
                return conversation

        return None

    async def create_direct_conversation(
        self,
        db,
        *,
        creator_user_id: int,
        other_user_id: int,
    ) -> ChatConversation:
        if creator_user_id == other_user_id:
            raise ValueError(
                "Нельзя создать личный диалог "
                "с самим собой."
            )

        creator_result = await db.execute(
            select(User).where(
                User.id == creator_user_id,
                User.is_active.is_(True),
                User.status == "active",
            )
        )

        creator = (
            creator_result
            .scalar_one_or_none()
        )

        if creator is None:
            raise ValueError(
                "Отправитель не найден "
                "или его учётная запись неактивна."
            )

        other_user_result = await db.execute(
            select(User).where(
                User.id == other_user_id,
                User.is_active.is_(True),
                User.status == "active",
            )
        )

        other_user = (
            other_user_result
            .scalar_one_or_none()
        )

        if other_user is None:
            raise ValueError(
                "Получатель не найден "
                "или его учётная запись неактивна."
            )

        conversation = ChatConversation(
            conversation_type="direct",
            title=None,
            created_by_user_id=creator_user_id,
        )

        db.add(
            conversation
        )

        await db.flush()

        db.add_all(
            [
                ChatParticipant(
                    conversation_id=conversation.id,
                    user_id=creator_user_id,
                ),
                ChatParticipant(
                    conversation_id=conversation.id,
                    user_id=other_user_id,
                ),
            ]
        )

        await db.flush()

        return conversation

    async def get_or_create_direct_conversation(
        self,
        db,
        *,
        user_id: int,
        other_user_id: int,
    ) -> ChatConversation:
        if user_id == other_user_id:
            raise ValueError(
                "Нельзя создать личный диалог "
                "с самим собой."
            )

        conversation = (
            await self.get_direct_conversation(
                db,
                user_id,
                other_user_id,
            )
        )

        if conversation is not None:
            return conversation

        return await self.create_direct_conversation(
            db,
            creator_user_id=user_id,
            other_user_id=other_user_id,
        )

    async def get_conversation(
        self,
        db,
        conversation_id: int,
    ) -> ChatConversation | None:
        result = await db.execute(
            select(
                ChatConversation
            )
            .where(
                ChatConversation.id
                == conversation_id
            )
        )

        return (
            result
            .scalar_one_or_none()
        )

    async def get_participant(
        self,
        db,
        *,
        conversation_id: int,
        user_id: int,
    ) -> ChatParticipant | None:
        result = await db.execute(
            select(
                ChatParticipant
            )
            .where(
                ChatParticipant.conversation_id
                == conversation_id,
                ChatParticipant.user_id
                == user_id,
            )
        )

        return (
            result
            .scalar_one_or_none()
        )

    async def user_is_participant(
        self,
        db,
        *,
        conversation_id: int,
        user_id: int,
    ) -> bool:
        participant = (
            await self.get_participant(
                db,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        )

        return participant is not None

    async def get_other_user(
        self,
        db,
        *,
        conversation_id: int,
        user_id: int,
    ) -> User | None:
        result = await db.execute(
            select(
                User
            )
            .join(
                ChatParticipant,
                ChatParticipant.user_id
                == User.id,
            )
            .where(
                ChatParticipant.conversation_id
                == conversation_id,
                ChatParticipant.user_id
                != user_id,
            )
            .limit(1)
        )

        return (
            result
            .scalar_one_or_none()
        )

    async def send_message(
        self,
        db,
        *,
        conversation_id: int,
        sender_user_id: int,
        text: str,
    ) -> ChatMessage:
        text = text.strip()

        if not text:
            raise ValueError(
                "Сообщение не может быть пустым."
            )

        if len(text) > 10000:
            raise ValueError(
                "Сообщение слишком длинное."
            )

        conversation = (
            await self.get_conversation(
                db,
                conversation_id,
            )
        )

        if conversation is None:
            raise ValueError(
                "Диалог не найден."
            )

        is_participant = (
            await self.user_is_participant(
                db,
                conversation_id=conversation_id,
                user_id=sender_user_id,
            )
        )

        if not is_participant:
            raise PermissionError(
                "Пользователь не является "
                "участником этого диалога."
            )

        sender_result = await db.execute(
            select(User).where(
                User.id == sender_user_id,
                User.is_active.is_(True),
                User.status == "active",
            )
        )

        sender = (
            sender_result
            .scalar_one_or_none()
        )

        if sender is None:
            raise PermissionError(
                "Учётная запись отправителя "
                "неактивна."
            )

        message = ChatMessage(
            conversation_id=conversation_id,
            sender_user_id=sender_user_id,
            message_type="message",
            text=text,
            is_deleted=False,
        )

        db.add(
            message
        )

        conversation.updated_at = (
            datetime.utcnow()
        )

        await db.flush()

        return message

    async def get_messages(
        self,
        db,
        *,
        conversation_id: int,
        user_id: int,
        limit: int = 100,
    ) -> list[ChatMessage]:
        is_participant = (
            await self.user_is_participant(
                db,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        )

        if not is_participant:
            raise PermissionError(
                "Нет доступа к этому диалогу."
            )

        if limit < 1:
            limit = 1

        if limit > 200:
            limit = 200

        result = await db.execute(
            select(
                ChatMessage
            )
            .where(
                ChatMessage.conversation_id
                == conversation_id,
                ChatMessage.is_deleted.is_(
                    False
                ),
            )
            .order_by(
                ChatMessage.id.desc()
            )
            .limit(
                limit
            )
        )

        messages = list(
            result.scalars().all()
        )

        messages.reverse()

        return messages

    async def mark_as_read(
        self,
        db,
        *,
        conversation_id: int,
        user_id: int,
        message_id: int | None,
    ) -> None:
        participant = (
            await self.get_participant(
                db,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        )

        if participant is None:
            raise PermissionError(
                "Нет доступа к этому диалогу."
            )

        if message_id is None:
            return

        message_result = await db.execute(
            select(
                ChatMessage
            )
            .where(
                ChatMessage.id
                == message_id,
                ChatMessage.conversation_id
                == conversation_id,
                ChatMessage.is_deleted.is_(
                    False
                ),
            )
        )

        message = (
            message_result
            .scalar_one_or_none()
        )

        if message is None:
            raise ValueError(
                "Сообщение не найдено."
            )

        if (
            participant.last_read_message_id
            is None
            or message.id
            > participant.last_read_message_id
        ):
            participant.last_read_message_id = (
                message.id
            )

    async def get_unread_count(
        self,
        db,
        *,
        conversation_id: int,
        user_id: int,
        last_read_message_id: int | None,
    ) -> int:
        query = select(
            func.count(
                ChatMessage.id
            )
        ).where(
            ChatMessage.conversation_id
            == conversation_id,
            ChatMessage.is_deleted.is_(
                False
            ),
            ChatMessage.sender_user_id
            != user_id,
        )

        if last_read_message_id is not None:
            query = query.where(
                ChatMessage.id
                > last_read_message_id
            )

        result = await db.execute(
            query
        )

        return (
            result.scalar_one()
        )

    async def get_last_message(
        self,
        db,
        *,
        conversation_id: int,
    ) -> ChatMessage | None:
        result = await db.execute(
            select(
                ChatMessage
            )
            .where(
                ChatMessage.conversation_id
                == conversation_id,
                ChatMessage.is_deleted.is_(
                    False
                ),
            )
            .order_by(
                ChatMessage.id.desc()
            )
            .limit(1)
        )

        return (
            result
            .scalar_one_or_none()
        )

    async def get_user_conversations(
        self,
        db,
        *,
        user_id: int,
    ) -> list[dict]:
        participant_result = await db.execute(
            select(
                ChatParticipant
            )
            .where(
                ChatParticipant.user_id
                == user_id
            )
        )

        participants = list(
            participant_result
            .scalars()
            .all()
        )

        conversation_items = []

        for participant in participants:
            conversation = (
                await self.get_conversation(
                    db,
                    participant.conversation_id,
                )
            )

            if conversation is None:
                continue

            other_user = None

            if (
                conversation.conversation_type
                == "direct"
            ):
                other_user = (
                    await self.get_other_user(
                        db,
                        conversation_id=conversation.id,
                        user_id=user_id,
                    )
                )

            last_message = (
                await self.get_last_message(
                    db,
                    conversation_id=conversation.id,
                )
            )

            unread_count = (
                await self.get_unread_count(
                    db,
                    conversation_id=conversation.id,
                    user_id=user_id,
                    last_read_message_id=(
                        participant.last_read_message_id
                    ),
                )
            )

            conversation_items.append(
                {
                    "conversation": conversation,
                    "participant": participant,
                    "other_user": other_user,
                    "last_message": last_message,
                    "unread_count": unread_count,
                }
            )

        conversation_items.sort(
            key=lambda item: (
                item["conversation"].updated_at
            ),
            reverse=True,
        )

        return conversation_items


sd_chat_service = SDChatService()