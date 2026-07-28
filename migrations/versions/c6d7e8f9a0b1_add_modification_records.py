"""Add modification_records table (Art. 43 substantial modification tracking).

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-04-22 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "c6d7e8f9a0b1"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "modification_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            sa.String(255),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_from", sa.Integer, nullable=True),
        sa.Column("version_to", sa.Integer, nullable=True),
        sa.Column("modification_type", sa.String(40), nullable=False),
        sa.Column(
            "classification",
            sa.String(40),
            nullable=False,
            server_default="unclassified",
        ),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("impact_assessment", JSONB, nullable=True),
        sa.Column(
            "triggered_reassessment",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("reassessment_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("diff", JSONB, nullable=True),
        sa.Column("created_by", sa.String(255), nullable=False),
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
        "ix_modification_records_agent_id", "modification_records", ["agent_id"]
    )
    op.create_index(
        "ix_modification_records_classification",
        "modification_records",
        ["classification"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_modification_records_classification", table_name="modification_records"
    )
    op.drop_index("ix_modification_records_agent_id", table_name="modification_records")
    op.drop_table("modification_records")
