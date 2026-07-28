"""Add api_keys table and webhook_type column.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-04-15 13:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Scoped API keys
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("owner_role", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_hash", sa.Text, nullable=False, unique=True, index=True),
        sa.Column("scope", sa.String(50), nullable=False, server_default="admin"),
        sa.Column("revoked", sa.Boolean, server_default="false"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Slack webhook support
    op.add_column(
        "webhooks",
        sa.Column("webhook_type", sa.String(50), server_default="generic", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("webhooks", "webhook_type")
    op.drop_table("api_keys")
