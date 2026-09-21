from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from backend.app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    target_user_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    entity_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    before_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    after_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )