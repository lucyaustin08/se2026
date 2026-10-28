"""Member profile: phone number and secondary instrument

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_VALUES = ("rhythm_guitar_vocals", "lead_guitar", "bass", "drums", "specialty")


def upgrade() -> None:
    with op.batch_alter_table("members") as batch:
        batch.add_column(
            sa.Column(
                "secondary_role",
                sa.Enum(*ROLE_VALUES, name="member_secondary_role", native_enum=False),
                nullable=True,
            )
        )
        batch.add_column(sa.Column("phone", sa.String(length=40), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("members") as batch:
        batch.drop_column("phone")
        batch.drop_column("secondary_role")
