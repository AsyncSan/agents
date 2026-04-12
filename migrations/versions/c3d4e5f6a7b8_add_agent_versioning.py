"""add_agent_versioning

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-12 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add version column to agents
    op.add_column('agents', sa.Column('version', sa.Integer(), server_default='1', nullable=False))

    # Create agent_versions table
    op.create_table(
        'agent_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', sa.String(255), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('card', postgresql.JSONB(), nullable=False),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_versions_agent_id', 'agent_versions', ['agent_id'])


def downgrade() -> None:
    op.drop_table('agent_versions')
    op.drop_column('agents', 'version')
