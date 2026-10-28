"""One-off busy times

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "busy_times",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
            name=op.f("fk_busy_times_member_id_members"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_busy_times")),
    )
    op.create_index(op.f("ix_busy_times_member_id"), "busy_times", ["member_id"])
    op.create_index(op.f("ix_busy_times_starts_at"), "busy_times", ["starts_at"])
    op.create_index(op.f("ix_busy_times_ends_at"), "busy_times", ["ends_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_busy_times_ends_at"), table_name="busy_times")
    op.drop_index(op.f("ix_busy_times_starts_at"), table_name="busy_times")
    op.drop_index(op.f("ix_busy_times_member_id"), table_name="busy_times")
    op.drop_table("busy_times")
