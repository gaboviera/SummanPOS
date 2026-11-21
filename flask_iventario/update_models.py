import os

filepath = r"c:\Cursos\Python\SummanPOS\flask_iventario\models.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Añadir es_dropshipping a Productos
content = content.replace(
    "costo = db.Column(db.Numeric(10, 2), nullable=True, default=0.00)",
    "costo = db.Column(db.Numeric(10, 2), nullable=True, default=0.00)\n    es_dropshipping = db.Column(db.Boolean, default=False)"
)

content = content.replace(
    "def __init__(self, nombre, cantidad, precio, costo=0.00, descripcion=None, categoria_id=None):",
    "def __init__(self, nombre, cantidad, precio, costo=0.00, descripcion=None, categoria_id=None, es_dropshipping=False):"
)

content = content.replace(
    "self.categoria_id = categoria_id",
    "self.categoria_id = categoria_id\n        self.es_dropshipping = es_dropshipping"
)

# 2. Añadir estados de pago a OrdenDropshipping
content = content.replace(
    "ganancia = db.Column(db.Numeric(10, 2), default=0.00)",
    "ganancia = db.Column(db.Numeric(10, 2), default=0.00)\n    pago_cliente_estado = db.Column(db.String(20), default='Pendiente')\n    pago_proveedor_estado = db.Column(db.String(20), default='Pendiente')"
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Models updated successfully!")
