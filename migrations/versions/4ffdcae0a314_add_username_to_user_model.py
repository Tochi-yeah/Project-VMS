"""Add profile_picture to User model

Revision ID: 4ffdcae0a314
Revises: 5ec0e93e7750
Create Date: 2025-06-21 15:01:12.237276

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4ffdcae0a314'
down_revision = '5ec0e93e7750'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_picture', sa.String(length=255), nullable=True))

def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('profile_picture')