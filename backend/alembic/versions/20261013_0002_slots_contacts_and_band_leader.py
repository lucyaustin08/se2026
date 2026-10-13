"""Per-gig roles with invitations, a contact list, performance length and the band leader

Replaces fixed gig types and direct assignments (revision 0001) with:
- gig_slots: one row per role a gig needs, with who was invited and their answer
- gig_contacts: any number of contacts per gig
- gigs.performance_minutes: how long the gig runs after the first set
- members.is_band_leader

Existing assignments become pending invitations, and existing contact fields become
contacts, so a development database keeps its data.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_VALUES = ("rhythm_guitar_vocals", "lead_guitar", "bass", "drums", "specialty")
CONTACT_COLUMNS = ("name", "phone", "email")


def upgrade() -> None:
    with op.batch_alter_table("members") as batch:
        batch.add_column(
            sa.Column("is_band_leader", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    op.create_table(
        "gig_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gig_id", sa.Integer(), nullable=False),
        sa.Column(
            "role", sa.Enum(*ROLE_VALUES, name="slot_role", native_enum=False), nullable=False
        ),
        sa.Column("member_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "open", "invited", "accepted", "declined", name="slot_status", native_enum=False
            ),
            nullable=False,
        ),
        sa.Column("pay_cents", sa.Integer(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["gig_id"], ["gigs.id"], name=op.f("fk_gig_slots_gig_id_gigs"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["member_id"], ["members.id"], name=op.f("fk_gig_slots_member_id_members")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gig_slots")),
        sa.UniqueConstraint("gig_id", "member_id", name=op.f("uq_gig_slots_gig_id_member_id")),
        sa.UniqueConstraint("gig_id", "role", name=op.f("uq_gig_slots_gig_id_role")),
    )

    op.create_table(
        "gig_contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gig_id", sa.Integer(), nullable=False),
        sa.Column(
            "label",
            sa.Enum("venue", "booking", "other", name="contact_label", native_enum=False),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["gig_id"], ["gigs.id"], name=op.f("fk_gig_contacts_gig_id_gigs"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gig_contacts")),
    )

    # Carry existing data over before dropping the old columns and table.
    op.execute(
        "INSERT INTO gig_slots (gig_id, role, member_id, status, created_at) "
        "SELECT gig_id, slot, member_id, 'invited', created_at FROM gig_assignments"
    )
    for label in ("venue", "booking"):
        name, phone, email = (f"{label}_contact_{column}" for column in CONTACT_COLUMNS)
        op.execute(
            "INSERT INTO gig_contacts (gig_id, label, name, phone, email, created_at) "
            f"SELECT id, '{label}', {name}, {phone}, {email}, created_at FROM gigs "
            f"WHERE {name} IS NOT NULL OR {phone} IS NOT NULL OR {email} IS NOT NULL"
        )

    op.drop_table("gig_assignments")

    with op.batch_alter_table("gigs") as batch:
        batch.add_column(
            sa.Column("performance_minutes", sa.Integer(), nullable=False, server_default="180")
        )
        batch.drop_column("gig_type")
        for label in ("venue", "booking"):
            for column in CONTACT_COLUMNS:
                batch.drop_column(f"{label}_contact_{column}")


def downgrade() -> None:
    with op.batch_alter_table("gigs") as batch:
        batch.add_column(
            sa.Column(
                "gig_type",
                sa.Enum("full_band", "trio", "duo", name="gig_type", native_enum=False),
                nullable=True,
            )
        )
        for label in ("venue", "booking"):
            batch.add_column(sa.Column(f"{label}_contact_name", sa.String(200), nullable=True))
            batch.add_column(sa.Column(f"{label}_contact_phone", sa.String(40), nullable=True))
            batch.add_column(sa.Column(f"{label}_contact_email", sa.String(254), nullable=True))
        batch.drop_column("performance_minutes")

    # Keep the first contact of each label, the closest the old shape allows.
    for label in ("venue", "booking"):
        for column in CONTACT_COLUMNS:
            op.execute(
                f"UPDATE gigs SET {label}_contact_{column} = ("
                f"SELECT c.{column} FROM gig_contacts c "
                f"WHERE c.gig_id = gigs.id AND c.label = '{label}' ORDER BY c.id LIMIT 1)"
            )

    op.create_table(
        "gig_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gig_id", sa.Integer(), nullable=False),
        sa.Column(
            "slot", sa.Enum(*ROLE_VALUES, name="lineup_slot", native_enum=False), nullable=False
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
            ["member_id"], ["members.id"], name=op.f("fk_gig_assignments_member_id_members")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gig_assignments")),
        sa.UniqueConstraint(
            "gig_id", "member_id", name=op.f("uq_gig_assignments_gig_id_member_id")
        ),
        sa.UniqueConstraint("gig_id", "slot", name=op.f("uq_gig_assignments_gig_id_slot")),
    )
    op.execute(
        "INSERT INTO gig_assignments (gig_id, slot, member_id, created_at) "
        "SELECT gig_id, role, member_id, created_at FROM gig_slots WHERE member_id IS NOT NULL"
    )
    op.drop_table("gig_contacts")
    op.drop_table("gig_slots")

    with op.batch_alter_table("members") as batch:
        batch.drop_column("is_band_leader")
