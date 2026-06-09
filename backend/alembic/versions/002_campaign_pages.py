"""Add campaign_pages table

Revision ID: 002
Revises: 001
Create Date: 2026-06-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'campaign_pages',
        sa.Column('id',                 sa.String(),     nullable=False),
        sa.Column('slug',               sa.String(255),  nullable=False),
        sa.Column('avatar',             sa.String(100),  nullable=True),
        sa.Column('product',            sa.String(100),  nullable=True),
        sa.Column('market',             sa.String(50),   nullable=True),
        sa.Column('run_id',             sa.String(255),  nullable=True),
        sa.Column('headline',           sa.String(500),  nullable=True),
        sa.Column('subheadline',        sa.Text(),       nullable=True),
        sa.Column('lead_opening',       sa.Text(),       nullable=True),
        sa.Column('villain_paragraph',  sa.Text(),       nullable=True),
        sa.Column('method_steps',       sa.JSON(),       nullable=True),
        sa.Column('proof_block',        sa.Text(),       nullable=True),
        sa.Column('cta_primary',        sa.String(500),  nullable=True),
        sa.Column('cta_secondary',      sa.String(500),  nullable=True),
        sa.Column('compliance_footer',  sa.Text(),       nullable=True),
        sa.Column('ad_units',           sa.JSON(),       nullable=True),
        sa.Column('email_sequence',     sa.JSON(),       nullable=True),
        sa.Column('is_published',       sa.Boolean(),    nullable=False, server_default='0'),
        sa.Column('created_by',         sa.String(100),  nullable=True),
        sa.Column('created_at',         sa.DateTime(),   nullable=False),
        sa.Column('published_at',       sa.DateTime(),   nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    op.create_index('ix_campaign_pages_slug', 'campaign_pages', ['slug'])


def downgrade() -> None:
    op.drop_index('ix_campaign_pages_slug', table_name='campaign_pages')
    op.drop_table('campaign_pages')
