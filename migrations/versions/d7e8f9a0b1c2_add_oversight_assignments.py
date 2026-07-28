"""Add oversight_assignments table (Art. 14 + 26(2)).

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-04-22 16:30:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision = "d7e8f9a0b1c2"
down_revision = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oversight_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), nullable=False),
        sa.Column("org_role", sa.String(20), nullable=False),
        sa.Column("staff_name", sa.String(255), nullable=False),
        sa.Column("staff_email", sa.String(255), nullable=False),
        sa.Column("staff_role_title", sa.String(255), nullable=True),
        sa.Column("oversight_role", sa.String(40), nullable=False),
        sa.Column("authority_level", sa.String(40), nullable=False),
        sa.Column("assigned_agent_ids", ARRAY(sa.String(255)), nullable=True),
        sa.Column("training_certificates", JSONB, nullable=True),
        sa.Column("competence_notes", sa.Text, nullable=True),
        sa.Column("authority_source", sa.Text, nullable=True),
        sa.Column("assigned_by", sa.String(255), nullable=True),
        sa.Column(
            "active",
            sa.Boolean,
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_oversight_assignments_org_id", "oversight_assignments", ["org_id"]
    )
    op.create_index(
        "ix_oversight_assignments_staff_email",
        "oversight_assignments",
        ["staff_email"],
    )
    op.create_index(
        "ix_oversight_assignments_oversight_role",
        "oversight_assignments",
        ["oversight_role"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_oversight_assignments_oversight_role", table_name="oversight_assignments"
    )
    op.drop_index(
        "ix_oversight_assignments_staff_email", table_name="oversight_assignments"
    )
    op.drop_index(
        "ix_oversight_assignments_org_id", table_name="oversight_assignments"
    )
    op.drop_table("oversight_assignments")
