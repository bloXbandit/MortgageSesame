"""Add flyer_image_url to campaign_pages

Connects the flyer builder to the campaign system.
A campaign page can now store a reference to a generated flyer image
so the visual creative travels with the campaign copy.

Revision ID: 005
Revises: 004
"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'campaign_pages',
        sa.Column('flyer_image_url', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('campaign_pages', 'flyer_image_url')
