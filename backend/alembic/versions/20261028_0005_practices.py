"""One-time practices and practice invitations

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "practices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("length_minutes", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("scheduled_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["scheduled_by_id"],
            ["members.id"],
            name=op.f("fk_practices_scheduled_by_id_members"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practices")),
    )
    op.create_index(op.f("ix_practices_starts_at"), "practices", ["starts_at"])

    op.create_table(
        "practice_invitations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("practice_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("invited", "accepted", "declined", name="invitation_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["practice_id"],
            ["practices.id"],
            name=op.f("fk_practice_invitations_practice_id_practices"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
            name=op.f("fk_practice_invitations_member_id_members"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practice_invitations")),
        sa.UniqueConstraint(
            "practice_id",
            "member_id",
            name=op.f("uq_practice_invitations_practice_id_member_id"),
        ),
    )


def downgrade() -> None:
    op.drop_table("practice_invitations")
    op.drop_index(op.f("ix_practices_starts_at"), table_name="practices")
    op.drop_table("practices")
