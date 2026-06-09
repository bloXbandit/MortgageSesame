"""Add notes and target_price columns to lead_intakes

These fields were referenced in agent write endpoints but never
actually existed as mapped columns, so writes were silently dropped.

Revision ID: 007
Revises: 006
"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('lead_intakes', sa.Column('notes',        sa.Text(),  nullable=True))
    op.add_column('lead_intakes', sa.Column('target_price', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('lead_intakes', 'target_price')
    op.drop_column('lead_intakes', 'notes')
