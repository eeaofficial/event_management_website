"""Increase sponsor logo length

Revision ID: 79d063bda6e2
Revises: 8efb0962ea27
Create Date: 2026-02-17 14:44:11.050925

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '79d063bda6e2'
down_revision = '8efb0962ea27'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('sponsor', schema=None) as batch_op:
        batch_op.alter_column(
            'logo',
            existing_type=sa.VARCHAR(length=255),
            type_=sa.Text(),
            existing_nullable=False
        )


def downgrade():
    with op.batch_alter_table('sponsor', schema=None) as batch_op:
        batch_op.alter_column(
            'logo',
            existing_type=sa.Text(),
            type_=sa.VARCHAR(length=255),
            existing_nullable=False
        )
