"""add tipo to contactos

Revision ID: 0002_add_tipo_to_contactos
Revises: 0001_baseline
Create Date: 2026-09-07 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '0002_add_tipo_to_contactos'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [c['name'] for c in inspector.get_columns('contactos')]
    if 'tipo' not in cols:
        with op.batch_alter_table('contactos', schema=None) as batch_op:
            batch_op.add_column(sa.Column('tipo', sa.String(length=50), server_default='Cliente', nullable=False))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [c['name'] for c in inspector.get_columns('contactos')]
    if 'tipo' in cols:
        with op.batch_alter_table('contactos', schema=None) as batch_op:
            batch_op.drop_column('tipo')
