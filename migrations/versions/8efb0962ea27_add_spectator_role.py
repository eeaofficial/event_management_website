"""add spectator role

Revision ID: 8efb0962ea27
Revises: 7d95ed01b93b
Create Date: 2026-02-10 20:43:45.578880

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8efb0962ea27'
down_revision = '7d95ed01b93b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column(
            'isSpectator',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        )
    )


def downgrade():
    op.drop_column('users', 'isSpectator')