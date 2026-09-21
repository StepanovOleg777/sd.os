from sqlalchemy import (
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


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    code: Mapped[str] = mapped_column(
        String(128),
        unique=True,
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


class RolePermission(Base):
    __tablename__ = "role_permissions"

    __table_args__ = (
        UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permission",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey(
            "roles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    permission_id: Mapped[int] = mapped_column(
        ForeignKey(
            "permissions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    scope_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="all",
    )


class UserPermission(Base):
    __tablename__ = "user_permissions"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "permission_id",
            name="uq_user_permission",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    permission_id: Mapped[int] = mapped_column(
        ForeignKey(
            "permissions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    scope_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="all",
    )


class UserPermissionTarget(Base):
    __tablename__ = "user_permission_targets"

    __table_args__ = (
        UniqueConstraint(
            "user_permission_id",
            "target_type",
            "target_id",
            name="uq_user_permission_target",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    user_permission_id: Mapped[int] = mapped_column(
        ForeignKey(
            "user_permissions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    target_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    target_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )