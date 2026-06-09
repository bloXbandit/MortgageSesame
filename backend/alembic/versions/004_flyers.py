"""004 flyers and reference photos

Revision ID: 004
Revises: 003
Create Date: 2026-06-03
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'reference_photos',
        sa.Column('id',          sa.Integer(),  primary_key=True),
        sa.Column('file_path',   sa.String(),   nullable=True),
        sa.Column('file_url',    sa.String(),   nullable=True),
        sa.Column('uploaded_by', sa.String(),   nullable=True),
        sa.Column('created_at',  sa.DateTime(), nullable=True),
        sa.Column('updated_at',  sa.DateTime(), nullable=True),
    )

    op.create_table(
        'generated_flyers',
        sa.Column('id',                sa.Integer(),  primary_key=True),
        sa.Column('use_case',          sa.String(),   nullable=True),
        sa.Column('flyer_format',      sa.String(),   nullable=True),
        sa.Column('avatar_style',      sa.Text(),     nullable=True),
        sa.Column('headline',          sa.String(),   nullable=True),
        sa.Column('subheadline',       sa.String(),   nullable=True),
        sa.Column('cta_text',          sa.String(),   nullable=True),
        sa.Column('provider',          sa.String(),   nullable=True),
        sa.Column('avatar_image_path', sa.String(),   nullable=True),
        sa.Column('avatar_image_url',  sa.String(),   nullable=True),
        sa.Column('flyer_image_path',  sa.String(),   nullable=True),
        sa.Column('flyer_image_url',   sa.String(),   nullable=True),
        sa.Column('status',            sa.String(),   nullable=True),
        sa.Column('error',             sa.Text(),     nullable=True),
        sa.Column('created_by',        sa.String(),   nullable=True),
        sa.Column('created_at',        sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('generated_flyers')
    op.drop_table('reference_photos')
