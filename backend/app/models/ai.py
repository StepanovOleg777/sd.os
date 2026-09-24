from datetime import (
    datetime,
    timezone,
)

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)
from uuid6 import uuid7

from backend.app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


# =========================================================
# AI PROJECT
# =========================================================


class AIProject(Base):
    __tablename__ = "ai_projects"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    public_id = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
        default=uuid7,
    )

    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="private",
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


# =========================================================
# AI CONVERSATION
# =========================================================


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    public_id = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
        default=uuid7,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    project_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "ai_projects.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


# =========================================================
# AI MESSAGE
# =========================================================


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey(
            "ai_conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )


# =========================================================
# AI PROVIDER STATE
# =========================================================


class AIProviderState(Base):
    __tablename__ = "ai_provider_states"

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "provider_code",
            "context_key",
            name="uq_ai_provider_state_context",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey(
            "ai_conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    provider_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    context_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="supervisor",
    )

    model_code: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    state: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


# =========================================================
# AI RUN
# =========================================================


class AIRun(Base):
    __tablename__ = "ai_runs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    trace_id = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
        default=uuid7,
    )

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey(
            "ai_conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    parent_run_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "ai_runs.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    agent_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="supervisor",
        index=True,
    )

    capability: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    provider_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    model_code: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    provider_response_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="running",
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )