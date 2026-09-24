"""добавлены таблицы AI контекста

Revision ID: 05687dbce2a4
Revises: 9f3c2d7b8a11
Create Date: 2026-09-24 19:28:16.281778

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "05687dbce2a4"
down_revision: Union[str, Sequence[str], None] = "9f3c2d7b8a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "ai_projects",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "public_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "owner_user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "visibility",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
    )

    op.create_index(
        op.f(
            "ix_ai_projects_owner_user_id"
        ),
        "ai_projects",
        ["owner_user_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_projects_public_id"
        ),
        "ai_projects",
        ["public_id"],
        unique=True,
    )

    op.create_index(
        op.f(
            "ix_ai_projects_status"
        ),
        "ai_projects",
        ["status"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_projects_visibility"
        ),
        "ai_projects",
        ["visibility"],
        unique=False,
    )

    op.create_table(
        "ai_conversations",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "public_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.BigInteger(),
            nullable=True,
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["ai_projects.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
    )

    op.create_index(
        op.f(
            "ix_ai_conversations_project_id"
        ),
        "ai_conversations",
        ["project_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_conversations_public_id"
        ),
        "ai_conversations",
        ["public_id"],
        unique=True,
    )

    op.create_index(
        op.f(
            "ix_ai_conversations_status"
        ),
        "ai_conversations",
        ["status"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_conversations_user_id"
        ),
        "ai_conversations",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "ai_messages",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "text",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["ai_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
    )

    op.create_index(
        op.f(
            "ix_ai_messages_conversation_id"
        ),
        "ai_messages",
        ["conversation_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_messages_created_at"
        ),
        "ai_messages",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_messages_role"
        ),
        "ai_messages",
        ["role"],
        unique=False,
    )

    op.create_table(
        "ai_provider_states",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "provider_code",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "context_key",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "model_code",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "state",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["ai_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "provider_code",
            "context_key",
            name="uq_ai_provider_state_context",
        ),
    )

    op.create_index(
        op.f(
            "ix_ai_provider_states_conversation_id"
        ),
        "ai_provider_states",
        ["conversation_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_provider_states_provider_code"
        ),
        "ai_provider_states",
        ["provider_code"],
        unique=False,
    )

    op.create_table(
        "ai_runs",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "trace_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "parent_run_id",
            sa.BigInteger(),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "agent_code",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "capability",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "provider_code",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "model_code",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "provider_response_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["ai_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_run_id"],
            ["ai_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
    )

    op.create_index(
        op.f(
            "ix_ai_runs_agent_code"
        ),
        "ai_runs",
        ["agent_code"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_runs_capability"
        ),
        "ai_runs",
        ["capability"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_runs_conversation_id"
        ),
        "ai_runs",
        ["conversation_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_runs_parent_run_id"
        ),
        "ai_runs",
        ["parent_run_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_runs_provider_code"
        ),
        "ai_runs",
        ["provider_code"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_runs_started_at"
        ),
        "ai_runs",
        ["started_at"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_runs_status"
        ),
        "ai_runs",
        ["status"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_ai_runs_trace_id"
        ),
        "ai_runs",
        ["trace_id"],
        unique=True,
    )

    op.create_index(
        op.f(
            "ix_ai_runs_user_id"
        ),
        "ai_runs",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f(
            "ix_ai_runs_user_id"
        ),
        table_name="ai_runs",
    )

    op.drop_index(
        op.f(
            "ix_ai_runs_trace_id"
        ),
        table_name="ai_runs",
    )

    op.drop_index(
        op.f(
            "ix_ai_runs_status"
        ),
        table_name="ai_runs",
    )

    op.drop_index(
        op.f(
            "ix_ai_runs_started_at"
        ),
        table_name="ai_runs",
    )

    op.drop_index(
        op.f(
            "ix_ai_runs_provider_code"
        ),
        table_name="ai_runs",
    )

    op.drop_index(
        op.f(
            "ix_ai_runs_parent_run_id"
        ),
        table_name="ai_runs",
    )

    op.drop_index(
        op.f(
            "ix_ai_runs_conversation_id"
        ),
        table_name="ai_runs",
    )

    op.drop_index(
        op.f(
            "ix_ai_runs_capability"
        ),
        table_name="ai_runs",
    )

    op.drop_index(
        op.f(
            "ix_ai_runs_agent_code"
        ),
        table_name="ai_runs",
    )

    op.drop_table(
        "ai_runs"
    )

    op.drop_index(
        op.f(
            "ix_ai_provider_states_provider_code"
        ),
        table_name="ai_provider_states",
    )

    op.drop_index(
        op.f(
            "ix_ai_provider_states_conversation_id"
        ),
        table_name="ai_provider_states",
    )

    op.drop_table(
        "ai_provider_states"
    )

    op.drop_index(
        op.f(
            "ix_ai_messages_role"
        ),
        table_name="ai_messages",
    )

    op.drop_index(
        op.f(
            "ix_ai_messages_created_at"
        ),
        table_name="ai_messages",
    )

    op.drop_index(
        op.f(
            "ix_ai_messages_conversation_id"
        ),
        table_name="ai_messages",
    )

    op.drop_table(
        "ai_messages"
    )

    op.drop_index(
        op.f(
            "ix_ai_conversations_user_id"
        ),
        table_name="ai_conversations",
    )

    op.drop_index(
        op.f(
            "ix_ai_conversations_status"
        ),
        table_name="ai_conversations",
    )

    op.drop_index(
        op.f(
            "ix_ai_conversations_public_id"
        ),
        table_name="ai_conversations",
    )

    op.drop_index(
        op.f(
            "ix_ai_conversations_project_id"
        ),
        table_name="ai_conversations",
    )

    op.drop_table(
        "ai_conversations"
    )

    op.drop_index(
        op.f(
            "ix_ai_projects_visibility"
        ),
        table_name="ai_projects",
    )

    op.drop_index(
        op.f(
            "ix_ai_projects_status"
        ),
        table_name="ai_projects",
    )

    op.drop_index(
        op.f(
            "ix_ai_projects_public_id"
        ),
        table_name="ai_projects",
    )

    op.drop_index(
        op.f(
            "ix_ai_projects_owner_user_id"
        ),
        table_name="ai_projects",
    )

    op.drop_table(
        "ai_projects"
    )