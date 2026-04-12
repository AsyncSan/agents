"""add_ratings_table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ratings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', sa.String(255), sa.ForeignKey('tasks.id'), nullable=False, unique=True),
        sa.Column('consumer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('consumers.id'), nullable=False),
        sa.Column('agent_id', sa.String(255), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('score >= 1 AND score <= 5', name='ck_rating_score_range'),
    )
    op.create_index('ix_ratings_agent_id', 'ratings', ['agent_id'])


def downgrade() -> None:
    op.drop_table('ratings')
