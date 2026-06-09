"""Add listing agent fields to listings table

Allows a listing to carry the selling agent's name, phone, and email
either entered freeform or linked to an existing Contacts realtor record.

Revision ID: 006
Revises: 005
"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('listings', sa.Column('listing_agent_contact_id', sa.String(), nullable=True))
    op.add_column('listings', sa.Column('listing_agent_name',       sa.String(255), nullable=True))
    op.add_column('listings', sa.Column('listing_agent_phone',      sa.String(30),  nullable=True))
    op.add_column('listings', sa.Column('listing_agent_email',      sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('listings', 'listing_agent_email')
    op.drop_column('listings', 'listing_agent_phone')
    op.drop_column('listings', 'listing_agent_name')
    op.drop_column('listings', 'listing_agent_contact_id')
