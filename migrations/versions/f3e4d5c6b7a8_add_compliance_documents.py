"""Add compliance_documents table.

Revision ID: f3e4d5c6b7a8
Revises: e1f2a3b4c5d6
Create Date: 2026-04-21 19:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "f3e4d5c6b7a8"
down_revision = ("9ab23ca0e548", "f2a3b4c5d6e7")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), nullable=False),
        sa.Column("org_role", sa.String(20), nullable=False),
        sa.Column("doc_type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "agent_id",
            sa.String(255),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("agent_version", sa.Integer, nullable=True),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
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
        "ix_compliance_documents_org_id", "compliance_documents", ["org_id"]
    )
    op.create_index(
        "ix_compliance_documents_doc_type", "compliance_documents", ["doc_type"]
    )
    op.create_index(
        "ix_compliance_documents_agent_id", "compliance_documents", ["agent_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_compliance_documents_agent_id", table_name="compliance_documents")
    op.drop_index("ix_compliance_documents_doc_type", table_name="compliance_documents")
    op.drop_index("ix_compliance_documents_org_id", table_name="compliance_documents")
    op.drop_table("compliance_documents")
