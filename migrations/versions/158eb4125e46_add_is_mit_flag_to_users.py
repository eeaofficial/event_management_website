"""add is_mit flag to users

Revision ID: 158eb4125e46
Revises: 7af1d89b73b8
Create Date: 2026-02-10 12:37:21.112257

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '158eb4125e46'
down_revision = '7af1d89b73b8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column(
            'is_mit',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        )
    )

def downgrade():
    op.drop_column('users', 'is_mit')
