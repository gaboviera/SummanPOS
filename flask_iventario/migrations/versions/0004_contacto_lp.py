"""agregar lista_precio_id a contactos

Revision ID: 0004_contacto_lp
Revises: 0003_recuperar_atributos
Create Date: 2026-10-04 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_contacto_lp'
down_revision = '0003_recuperar_atributos'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('contactos', sa.Column('lista_precio_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_contactos_lista_precio',
        'contactos', 'listas_precios',
        ['lista_precio_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    op.drop_constraint('fk_contactos_lista_precio', 'contactos', type_='foreignkey')
    op.drop_column('contactos', 'lista_precio_id')
