"""Initial migration with Visitor added Unique code and qr code

Revision ID: 2fcbd06e3809
Revises: ac0ec7b11c0e
Create Date: 2025-08-22 12:46:34.095697

"""
from alembic import op
import sqlalchemy as sa
import secrets

# revision identifiers, used by Alembic.
revision = '2fcbd06e3809'
down_revision = 'ac0ec7b11c0e'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add columns as nullable
    with op.batch_alter_table('visitor', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unique_code', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('group_code', sa.String(length=32), nullable=True))

    # 2. Populate unique_code for existing rows
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT id FROM visitor WHERE unique_code IS NULL"))
    for row in result:
        code = secrets.token_urlsafe(12)
        conn.execute(sa.text("UPDATE visitor SET unique_code = :code WHERE id = :id"), {"code": code, "id": row.id})

    # 3. Alter column to NOT NULL and add unique constraint
    with op.batch_alter_table('visitor', schema=None) as batch_op:
        batch_op.alter_column('unique_code', nullable=False)
        batch_op.create_unique_constraint(None, ['unique_code'])

def downgrade():
    with op.batch_alter_table('visitor', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_column('group_code')
        batch_op.drop_column('unique_code')