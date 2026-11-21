"""recuperar atributos tamano y marca

Revision ID: 0003_recuperar_atributos
Revises: 0002_add_tipo_to_contactos
Create Date: 2026-09-09 14:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_recuperar_atributos'
down_revision = '0002_add_tipo_to_contactos'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE atributos SET deleted_at = NULL WHERE nombre ILIKE '%marca%' OR nombre ILIKE '%tama%';")
    op.execute("""
        UPDATE valores_atributos SET deleted_at = NULL 
        WHERE atributo_id IN (SELECT id FROM atributos WHERE nombre ILIKE '%marca%' OR nombre ILIKE '%tama%');
    """)


def downgrade():
    pass
