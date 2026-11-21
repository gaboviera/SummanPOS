"""add_ciudad_to_guias_and_contactos

Reemite la migracion que originalmente se genero como e1fec70652d9. Esa
revision quedo ocupada por e1fec70652d9_dummy.py (bridge para la BD de dev,
que ya la tenia estampada), asi que los cambios reales se aplican aqui.

Es idempotente: si la columna ya existe (caso dev), no hace nada.

Revision ID: f3c9a1b70d42
Revises: b00000000001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = 'f3c9a1b70d42'
down_revision = 'b00000000001'
branch_labels = None
depends_on = None


def _columns(table):
    insp = inspect(op.get_bind())
    try:
        return {c['name'] for c in insp.get_columns(table)}
    except Exception:
        return None  # la tabla no existe


def _add(table, column, type_, **kw):
    cols = _columns(table)
    if cols is None:
        print(f"  - tabla '{table}' no existe, se omite")
        return False
    if column in cols:
        print(f"  - {table}.{column} ya existe, se omite")
        return False
    op.add_column(table, sa.Column(column, type_, nullable=True, **kw))
    print(f"  + {table}.{column} agregada")
    return True


def _drop(table, column):
    cols = _columns(table)
    if cols and column in cols:
        op.drop_column(table, column)


def upgrade():
    _add('contactos', 'ciudad', sa.String(length=100))

    _add('guias_despacho', 'ciudad', sa.String(length=100))
    _add('guias_despacho', 'tasa_euro', sa.Numeric(precision=10, scale=4))
    if _add('guias_despacho', 'vendedor_id', sa.Integer()):
        op.create_foreign_key(
            'fk_guias_despacho_vendedor_id_usuarios',
            'guias_despacho', 'usuarios', ['vendedor_id'], ['id'],
        )

    if _add('productos', 'proveedor_id', sa.Integer()):
        op.create_foreign_key(
            'fk_productos_proveedor_id_contactos',
            'productos', 'contactos', ['proveedor_id'], ['id'],
        )


def downgrade():
    op.execute('ALTER TABLE productos DROP CONSTRAINT IF EXISTS fk_productos_proveedor_id_contactos')
    _drop('productos', 'proveedor_id')

    op.execute('ALTER TABLE guias_despacho DROP CONSTRAINT IF EXISTS fk_guias_despacho_vendedor_id_usuarios')
    _drop('guias_despacho', 'vendedor_id')
    _drop('guias_despacho', 'tasa_euro')
    _drop('guias_despacho', 'ciudad')

    _drop('contactos', 'ciudad')
