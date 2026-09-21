from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from backend.app.core.database import Base


# =========================================================
# CONVERSATIONS
# =========================================================


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    conversation_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="direct",
        index=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )


# =========================================================
# PARTICIPANTS
# =========================================================


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "user_id",
            name=(
                "uq_chat_participants_"
                "conversation_user"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey(
            "chat_conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    last_read_message_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "chat_messages.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )


# =========================================================
# MESSAGES
# =========================================================


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey(
            "chat_conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    sender_user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    message_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="message",
        index=True,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )


# =========================================================
# ANNOUNCEMENTS
# =========================================================


class ChatAnnouncement(Base):
    __tablename__ = "chat_announcements"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    author_user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    audience_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    requires_acknowledgement: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )


# =========================================================
# ANNOUNCEMENT DEPARTMENTS
# =========================================================


class ChatAnnouncementDepartment(Base):
    __tablename__ = "chat_announcement_departments"

    __table_args__ = (
        UniqueConstraint(
            "announcement_id",
            "department_id",
            name=(
                "uq_chat_announcement_departments_"
                "announcement_department"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    announcement_id: Mapped[int] = mapped_column(
        ForeignKey(
            "chat_announcements.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    department_id: Mapped[int] = mapped_column(
        ForeignKey(
            "departments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


# =========================================================
# ANNOUNCEMENT RECIPIENTS
# =========================================================


class ChatAnnouncementRecipient(Base):
    __tablename__ = "chat_announcement_recipients"

    __table_args__ = (
        UniqueConstraint(
            "announcement_id",
            "user_id",
            name=(
                "uq_chat_announcement_recipients_"
                "announcement_user"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    announcement_id: Mapped[int] = mapped_column(
        ForeignKey(
            "chat_announcements.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )