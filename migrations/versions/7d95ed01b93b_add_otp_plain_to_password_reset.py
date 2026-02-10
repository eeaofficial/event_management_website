"""add otp_plain to password reset

Revision ID: 7d95ed01b93b
Revises: 4af3ca94f368
Create Date: 2026-02-10 19:18:52.234318

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d95ed01b93b'
down_revision = '4af3ca94f368'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'password_reset_otps',
        sa.Column('otp_plain', sa.String(length=10))
    )

def downgrade():
    op.drop_column('password_reset_otps', 'otp_plain')
