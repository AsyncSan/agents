"""Add risk_class to agents and plan to consumers.

Revision ID: e1f2a3b4c5d6
Revises: f37df764e6ae
Create Date: 2026-04-15 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "e1f2a3b4c5d6"
down_revision = "f37df764e6ae"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("risk_class", sa.String(50), server_default="minimal", nullable=False),
    )
    op.add_column(
        "consumers",
        sa.Column("plan", sa.String(50), server_default="starter", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("consumers", "plan")
    op.drop_column("agents", "risk_class")
