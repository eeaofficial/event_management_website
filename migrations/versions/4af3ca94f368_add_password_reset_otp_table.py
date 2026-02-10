"""add password reset otp table

Revision ID: 4af3ca94f368
Revises: 158eb4125e46
Create Date: 2026-02-10 14:12:38.867880

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4af3ca94f368'
down_revision = '158eb4125e46'
branch_labels = None
depends_on = None


from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'password_reset_otps',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reg_no', sa.String(length=30), nullable=False),
        sa.Column('mobile', sa.String(length=15), nullable=False),
        sa.Column('otp_hash', sa.String(length=128)),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )

def downgrade():
    op.drop_table('password_reset_otps')
