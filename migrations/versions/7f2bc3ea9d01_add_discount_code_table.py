"""add discount code table

Revision ID: 7f2bc3ea9d01
Revises: 111f12be1b75
Create Date: 2026-02-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7f2bc3ea9d01'
down_revision = '111f12be1b75'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'discount_code',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('percentage', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )


def downgrade():
    op.drop_table('discount_code')
