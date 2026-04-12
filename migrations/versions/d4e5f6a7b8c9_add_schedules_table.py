"""add_schedules_table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-12 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('consumer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('consumers.id'), nullable=False),
        sa.Column('agent_id', sa.String(255), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('cron_expression', sa.String(100), nullable=False),
        sa.Column('timezone', sa.String(50), server_default='UTC', nullable=False),
        sa.Column('inputs', postgresql.JSONB(), nullable=True),
        sa.Column('constraints', postgresql.JSONB(), nullable=True),
        sa.Column('callback_url', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default='true'),
        sa.Column('total_runs', sa.Integer(), server_default='0'),
        sa.Column('last_run_at', sa.Text(), nullable=True),
        sa.Column('next_run_at', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_schedules_consumer_id', 'schedules', ['consumer_id'])


def downgrade() -> None:
    op.drop_table('schedules')
