from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision = 'b00000000001'
down_revision = 'e1fec70652d9'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    conn.execute(text('''
        INSERT INTO listas_precios (id, nombre, tipo, basado_en, operador, valor_regla, activa, moneda) 
        VALUES (2, 'Mayorista', 'Porcentaje', 'precio_base', '-', 15.00, true, 'USD') 
        ON CONFLICT (id) DO NOTHING;
        
        INSERT INTO listas_precios (id, nombre, tipo, basado_en, operador, valor_regla, activa, moneda) 
        VALUES (3, 'Precio USDT', 'Porcentaje', 'precio_base', '+', 0.00, true, 'USDT') 
        ON CONFLICT (id) DO NOTHING;
        
        INSERT INTO listas_precios (id, nombre, tipo, basado_en, operador, valor_regla, activa, moneda) 
        VALUES (4, 'Precio Euro', 'Porcentaje', 'precio_base', '+', 0.00, true, 'EURO') 
        ON CONFLICT (id) DO NOTHING;
        
        INSERT INTO listas_precios (id, nombre, tipo, basado_en, operador, valor_regla, activa, moneda) 
        VALUES (1, 'Precio BCV', 'Porcentaje', 'precio_base', '+', 20.00, true, 'BCV') 
        ON CONFLICT (id) DO NOTHING;
        
        SELECT pg_catalog.setval('public.listas_precios_id_seq', 4, true);
    '''))

def downgrade():
    conn = op.get_bind()
    conn.execute(text('DELETE FROM listas_precios WHERE id IN (1, 2, 3, 4);'))
