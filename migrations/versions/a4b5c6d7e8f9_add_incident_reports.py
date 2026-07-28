"""Add incident_reports table.

Revision ID: a4b5c6d7e8f9
Revises: f3e4d5c6b7a8
Create Date: 2026-04-22 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "a4b5c6d7e8f9"
down_revision = "f3e4d5c6b7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incident_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), nullable=False),
        sa.Column("org_role", sa.String(20), nullable=False),
        sa.Column(
            "agent_id",
            sa.String(255),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("agent_version", sa.Integer, nullable=True),
        sa.Column(
            "task_id",
            sa.String(255),
            sa.ForeignKey("tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("awareness_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("affected_persons_estimate", sa.Integer, nullable=True),
        sa.Column("root_cause", sa.Text, nullable=True),
        sa.Column("mitigation_taken", sa.Text, nullable=True),
        sa.Column("mitigation_planned", sa.Text, nullable=True),
        sa.Column("reported_to_authority_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authority_name", sa.String(255), nullable=True),
        sa.Column("authority_reference", sa.String(255), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("extra", JSONB, nullable=True),
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
    op.create_index("ix_incident_reports_org_id", "incident_reports", ["org_id"])
    op.create_index("ix_incident_reports_agent_id", "incident_reports", ["agent_id"])
    op.create_index("ix_incident_reports_severity", "incident_reports", ["severity"])
    op.create_index("ix_incident_reports_status", "incident_reports", ["status"])


def downgrade() -> None:
    op.drop_index("ix_incident_reports_status", table_name="incident_reports")
    op.drop_index("ix_incident_reports_severity", table_name="incident_reports")
    op.drop_index("ix_incident_reports_agent_id", table_name="incident_reports")
    op.drop_index("ix_incident_reports_org_id", table_name="incident_reports")
    op.drop_table("incident_reports")
