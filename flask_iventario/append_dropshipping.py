
# ==========================================
# MÓDULO DE DROPSHIPPING
# ==========================================
class OrdenDropshipping(db.Model):
    __tablename__ = 'ordenes_dropshipping'
    id = db.Column(db.Integer, primary_key=True)
    referencia = db.Column(db.String(50), unique=True, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('contactos.id'), nullable=False)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('contactos.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(50), default='Pendiente') # Pendiente, Procesando, Enviado, Entregado, Cancelado
    empresa_transporte = db.Column(db.String(100), nullable=True)
    numero_seguimiento = db.Column(db.String(100), nullable=True)
    costo_total = db.Column(db.Numeric(10, 2), default=0.00)
    venta_total = db.Column(db.Numeric(10, 2), default=0.00)
    ganancia = db.Column(db.Numeric(10, 2), default=0.00)
    
    # Nuevos estados de pago
    pago_cliente_estado = db.Column(db.String(20), default='Pendiente') # Pendiente, Parcial, Pagado
    pago_proveedor_estado = db.Column(db.String(20), default='Pendiente') # Pendiente, Parcial, Pagado

    cliente = db.relationship('Contactos', foreign_keys=[cliente_id], backref='dropshipping_cliente')
    proveedor = db.relationship('Contactos', foreign_keys=[proveedor_id], backref='dropshipping_proveedor')
    detalles = db.relationship('DetalleDropshipping', backref='orden', lazy=True, cascade='all, delete-orphan')

class DetalleDropshipping(db.Model):
    __tablename__ = 'detalle_dropshipping'
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('ordenes_dropshipping.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    costo_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    precio_venta_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    
    producto = db.relationship('Productos', backref='detalles_dropshipping')
