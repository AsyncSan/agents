"""Add audit_shares table (read-only auditor tokens).

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-04-22 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "e8f9a0b1c2d3"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_shares",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), nullable=False),
        sa.Column("org_role", sa.String(20), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("token_prefix", sa.String(12), nullable=False),
        sa.Column("scope_agent_id", sa.String(255), nullable=True),
        sa.Column("auditor_name", sa.String(255), nullable=True),
        sa.Column("auditor_organisation", sa.String(255), nullable=True),
        sa.Column("auditor_email", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "access_count", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_audit_shares_org_id", "audit_shares", ["org_id"])
    op.create_index("ix_audit_shares_token_hash", "audit_shares", ["token_hash"])


def downgrade() -> None:
    op.drop_index("ix_audit_shares_token_hash", table_name="audit_shares")
    op.drop_index("ix_audit_shares_org_id", table_name="audit_shares")
    op.drop_table("audit_shares")
