from sqlalchemy import (
    Boolean,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from backend.app.core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )