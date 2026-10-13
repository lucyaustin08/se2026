"""Members, gigs and gig lineup assignments

Revision ID: 0001
Revises:
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_VALUES = ("rhythm_guitar_vocals", "lead_guitar", "bass", "drums", "specialty")


def upgrade() -> None:
    op.create_table(
        "members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column(
            "primary_role",
            sa.Enum(*ROLE_VALUES, name="member_role", native_enum=False),
            nullable=True,
        ),
        sa.Column("is_manager", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_members")),
        sa.UniqueConstraint("email", name=op.f("uq_members_email")),
    )

    op.create_table(
        "gigs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("potential", "booked", "cancelled", name="gig_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("first_set_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("load_in_offset_minutes", sa.Integer(), nullable=False),
        sa.Column("soundcheck_offset_minutes", sa.Integer(), nullable=False),
        sa.Column("venue_name", sa.String(length=200), nullable=True),
        sa.Column("venue_address", sa.String(length=300), nullable=True),
        sa.Column(
            "gig_type",
            sa.Enum("full_band", "trio", "duo", name="gig_type", native_enum=False),
            nullable=True,
        ),
        sa.Column("pay_cents", sa.Integer(), nullable=True),
        sa.Column("venue_contact_name", sa.String(length=200), nullable=True),
        sa.Column("venue_contact_phone", sa.String(length=40), nullable=True),
        sa.Column("venue_contact_email", sa.String(length=254), nullable=True),
        sa.Column("booking_contact_name", sa.String(length=200), nullable=True),
        sa.Column("booking_contact_phone", sa.String(length=40), nullable=True),
        sa.Column("booking_contact_email", sa.String(length=254), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gigs")),
    )
    op.create_index(op.f("ix_gigs_first_set_at"), "gigs", ["first_set_at"], unique=False)

    op.create_table(
        "gig_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gig_id", sa.Integer(), nullable=False),
        sa.Column(
            "slot",
            sa.Enum(*ROLE_VALUES, name="lineup_slot", native_enum=False),
            nullable=False,
        ),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["gig_id"],
            ["gigs.id"],
            name=op.f("fk_gig_assignments_gig_id_gigs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
            name=op.f("fk_gig_assignments_member_id_members"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gig_assignments")),
        sa.UniqueConstraint(
            "gig_id", "member_id", name=op.f("uq_gig_assignments_gig_id_member_id")
        ),
        sa.UniqueConstraint("gig_id", "slot", name=op.f("uq_gig_assignments_gig_id_slot")),
    )


def downgrade() -> None:
    op.drop_table("gig_assignments")
    op.drop_index(op.f("ix_gigs_first_set_at"), table_name="gigs")
    op.drop_table("gigs")
    op.drop_table("members")
