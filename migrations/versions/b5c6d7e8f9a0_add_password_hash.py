"""Add password_hash columns to providers and consumers.

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-04-22 15:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "b5c6d7e8f9a0"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "providers",
        sa.Column("password_hash", sa.Text, nullable=True),
    )
    op.add_column(
        "consumers",
        sa.Column("password_hash", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("consumers", "password_hash")
    op.drop_column("providers", "password_hash")
