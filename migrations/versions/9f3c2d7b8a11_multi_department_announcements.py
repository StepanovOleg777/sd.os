from alembic import op
import sqlalchemy as sa


revision = "9f3c2d7b8a11"
down_revision = "7ef8acba45b0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chat_announcement_departments",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "announcement_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "department_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["announcement_id"],
            ["chat_announcements.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
        sa.UniqueConstraint(
            "announcement_id",
            "department_id",
            name=(
                "uq_chat_announcement_departments_"
                "announcement_department"
            ),
        ),
    )

    op.create_index(
        op.f(
            "ix_chat_announcement_departments_"
            "announcement_id"
        ),
        "chat_announcement_departments",
        ["announcement_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_chat_announcement_departments_"
            "department_id"
        ),
        "chat_announcement_departments",
        ["department_id"],
        unique=False,
    )

    op.drop_index(
        op.f(
            "ix_chat_announcements_"
            "department_id"
        ),
        table_name="chat_announcements",
    )

    op.drop_constraint(
        "chat_announcements_department_id_fkey",
        "chat_announcements",
        type_="foreignkey",
    )

    op.drop_column(
        "chat_announcements",
        "department_id",
    )


def downgrade():
    op.add_column(
        "chat_announcements",
        sa.Column(
            "department_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "chat_announcements_department_id_fkey",
        "chat_announcements",
        "departments",
        ["department_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        op.f(
            "ix_chat_announcements_"
            "department_id"
        ),
        "chat_announcements",
        ["department_id"],
        unique=False,
    )

    op.drop_index(
        op.f(
            "ix_chat_announcement_departments_"
            "department_id"
        ),
        table_name=(
            "chat_announcement_departments"
        ),
    )

    op.drop_index(
        op.f(
            "ix_chat_announcement_departments_"
            "announcement_id"
        ),
        table_name=(
            "chat_announcement_departments"
        ),
    )

    op.drop_table(
        "chat_announcement_departments"
    )