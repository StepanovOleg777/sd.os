from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from backend.app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    fio: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    username: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    department_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "departments.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="invited",
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )