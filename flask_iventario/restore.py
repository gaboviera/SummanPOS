class DetalleDropshipping(db.Model):
    __tablename__ = 'detalle_dropshipping'
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('ordenes_dropshipping.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    costo_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    precio_venta_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    
    producto = db.relationship('Productos', backref='detalles_dropshipping')
