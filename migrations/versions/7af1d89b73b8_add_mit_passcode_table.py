"""add mit passcode table

Revision ID: 7af1d89b73b8
Revises: 
Create Date: 2026-02-10 11:36:06.047383

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7af1d89b73b8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'mit_passcodes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reg_no', sa.String(length=20), nullable=False),
        sa.Column('passcode', sa.String(length=20)),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )



def downgrade():
    op.drop_table('mit_passcodes')

    # ### end Alembic commands ###
