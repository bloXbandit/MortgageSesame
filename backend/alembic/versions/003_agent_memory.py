"""003 agent memory

Revision ID: 003
Revises: 002
Create Date: 2026-06-03
"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'agent_memory_logs',
        sa.Column('id',         sa.Integer(),  primary_key=True),
        sa.Column('run_id',     sa.String(),   nullable=True),
        sa.Column('run_type',   sa.String(),   nullable=True),
        sa.Column('summary',    sa.Text(),     nullable=True),
        sa.Column('actions_taken',       sa.JSON(), nullable=True),
        sa.Column('results',             sa.JSON(), nullable=True),
        sa.Column('needs_from_operator', sa.JSON(), nullable=True),
        sa.Column('status',     sa.String(),   nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_agent_memory_logs_run_id',   'agent_memory_logs', ['run_id'])
    op.create_index('ix_agent_memory_logs_run_type', 'agent_memory_logs', ['run_type'])

    op.create_table(
        'agent_asks',
        sa.Column('id',          sa.Integer(),  primary_key=True),
        sa.Column('question',    sa.Text(),     nullable=True),
        sa.Column('context',     sa.Text(),     nullable=True),
        sa.Column('urgency',     sa.String(),   nullable=True),
        sa.Column('category',    sa.String(),   nullable=True),
        sa.Column('is_resolved', sa.Boolean(),  default=False),
        sa.Column('resolution',  sa.Text(),     nullable=True),
        sa.Column('created_at',  sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('agent_asks')
    op.drop_index('ix_agent_memory_logs_run_type', 'agent_memory_logs')
    op.drop_index('ix_agent_memory_logs_run_id',   'agent_memory_logs')
    op.drop_table('agent_memory_logs')
