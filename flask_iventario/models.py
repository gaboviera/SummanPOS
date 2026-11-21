from extensions import db, login_manager
from flask_login import UserMixin
from datetime import datetime

class Rol(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    usuarios = db.relationship("Usuario", backref="rol", lazy=True)

class Usuario(db.Model, UserMixin):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    activo = db.Column(db.Boolean, default=True)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ==========================================
# NUEVO SISTEMA DE ATRIBUTOS (ESTILO ODOO)
# ==========================================
class Atributos(db.Model):
    __tablename__ = 'atributos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    valores = db.relationship('ValoresAtributos', backref='atributo', lazy=True)

class ValoresAtributos(db.Model):
    __tablename__ = 'valores_atributos'
    id = db.Column(db.Integer, primary_key=True)
    atributo_id = db.Column(db.Integer, db.ForeignKey('atributos.id'), nullable=False)
    valor = db.Column(db.String(100), nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

# Tabla puente invisible para asociar Valores a Productos (Muchos a Muchos)
productos_valores = db.Table('productos_valores',
    db.Column('producto_id', db.Integer, db.ForeignKey('productos.id'), primary_key=True),
    db.Column('valor_id', db.Integer, db.ForeignKey('valores_atributos.id'), primary_key=True)
)

class Categorias(db.Model): 
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), unique=True, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    productos = db.relationship('Productos', backref='categoria', lazy=True)

class Productos(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    
    # Llave foránea directa a la tabla de Categorías (Odoo: categ_id)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'))
    
    cantidad = db.Column(db.Integer, nullable=False)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    costo = db.Column(db.Numeric(10, 2), nullable=True, default=0.00)
    es_dropshipping = db.Column(db.Boolean, default=False)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('contactos.id'), nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    proveedor = db.relationship('Contactos', foreign_keys=[proveedor_id], backref='productos_dropshipping')

    @property
    def stock_entrante(self):
        # Lógica real para calcular stock entrante de órdenes en tránsito
        detalles = DetalleOrdenCompra.query.join(OrdenCompra).filter(
            DetalleOrdenCompra.producto_id == self.id,
            OrdenCompra.estado == 'En Tránsito'
        ).all()
        return sum((d.cantidad_pedida - (d.cantidad_recibida or 0)) for d in detalles)

    # Relación mágica con los atributos dinámicos
    valores = db.relationship('ValoresAtributos', secondary=productos_valores, lazy='subquery',
        backref=db.backref('productos', lazy=True))

    def __init__(self, nombre, cantidad, precio, costo=0.00, descripcion=None, categoria_id=None, es_dropshipping=False, proveedor_id=None):
        self.nombre = nombre
        self.cantidad = cantidad
        self.precio = precio
        self.costo = costo
        self.descripcion = descripcion
        self.categoria_id = categoria_id
        self.es_dropshipping = es_dropshipping
        self.proveedor_id = proveedor_id

# ==========================================
# TASAS DE CAMBIO (BCV)
# ==========================================
class TasaCambio(db.Model):
    __tablename__ = 'tasa_cambio'
    id = db.Column(db.Integer, primary_key=True)
    # Guardamos registros diferenciando por fuente y fecha
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    tasa = db.Column(db.Numeric(10, 4), nullable=False)
    fuente = db.Column(db.String(50), default='BCV')

# ==========================================
# TABLAS DE MOVIMIENTOS Y PROVEEDORES
# ==========================================
class Inventario(db.Model):
    __tablename__ = 'inventario'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'))
    cantidad = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.Date, nullable=False)

class Transacciones(db.Model):
    __tablename__ = 'transacciones'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'))
    cantidad = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(255), nullable=False)
    
    # --- NUEVAS LÍNEAS PARA EL HISTORIAL ---
    stock_anterior = db.Column(db.Integer, nullable=True)
    referencia = db.Column(db.String(50), nullable=True)  # <--- AÑADE ESTA LÍNEA
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=True)
    costo_unitario = db.Column(db.Numeric(10, 2), nullable=True)
    producto = db.relationship('Productos', backref='historial_movimientos')

 

class Proveedores(db.Model):
    __tablename__ = 'proveedores'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    informacion_contacto = db.Column(db.String(255), nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

class ProductosProveedores(db.Model):
    __tablename__ = 'productos_proveedores'
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), primary_key=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'), primary_key=True)

class GuiaDespacho(db.Model):
    __tablename__ = 'guias_despacho'
    id = db.Column(db.Integer, primary_key=True)
    referencia = db.Column(db.String(50), unique=True, nullable=False) # Ej: VTA-123456
    fecha = db.Column(db.DateTime, nullable=False)
    
    # Datos del Cliente
    cliente_nombre = db.Column(db.String(255), nullable=True)
    cliente_identificacion = db.Column(db.String(50), nullable=True) # RIF o CI
    cliente_direccion = db.Column(db.String(255), nullable=True)
    cliente_telefono = db.Column(db.String(50), nullable=True)
    ciudad = db.Column(db.String(100), nullable=True)
    
    # Datos Internos
    vendedor_nombre = db.Column(db.String(255), nullable=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    vendedor = db.relationship('Usuario', foreign_keys=[vendedor_id])
    observaciones = db.Column(db.Text, nullable=True)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    descuento_global = db.Column(db.Numeric(10, 2), nullable=True, default=0.0)
    tasa_bcv = db.Column(db.Numeric(10, 4), nullable=True)
    tasa_euro = db.Column(db.Numeric(10, 4), nullable=True)
    tasa_usdt = db.Column(db.Numeric(10, 4), nullable=True)
    estado = db.Column(db.String(20), nullable=False, default='Completada')
    
    # CxC
    estado_pago = db.Column(db.String(20), nullable=False, default='Pagada')
    monto_abonado = db.Column(db.Numeric(10, 2), nullable=True, default=0.0)
    fecha_vencimiento = db.Column(db.DateTime, nullable=True)
    pagos = db.relationship('PagosCxC', backref='guia', lazy=True, cascade='all, delete-orphan')

class Contactos(db.Model):
    __tablename__ = 'contactos'
    id = db.Column(db.Integer, primary_key=True)
    identificacion = db.Column(db.String(50), unique=True, nullable=False) # RIF o CI
    nombre = db.Column(db.String(255), nullable=False)
    correo = db.Column(db.String(150), nullable=True, unique=True)
    direccion = db.Column(db.String(255), nullable=True)
    ciudad = db.Column(db.String(100), nullable=True)
    telefono = db.Column(db.String(50), nullable=True)
    tipo = db.Column(db.String(50), nullable=False, default='Cliente') # 'Cliente', 'Proveedor', 'Ambos', 'Contacto Usuario', 'Sin Definir'
    deleted_at = db.Column(db.DateTime, nullable=True)
    lista_precio_id = db.Column(db.Integer, db.ForeignKey('listas_precios.id', ondelete='SET NULL'), nullable=True)
    lista_precio = db.relationship('ListasPrecios', foreign_keys=[lista_precio_id], lazy='joined')

# ==========================================
# LISTAS DE PRECIOS
# ==========================================
class ListasPrecios(db.Model):
    __tablename__ = 'listas_precios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    tipo = db.Column(db.String(50), default='Porcentaje') # Manual, Porcentaje, Fijo
    basado_en = db.Column(db.String(50), default='precio_base') # precio_base, costo
    operador = db.Column(db.String(10), default='+') # +, -
    valor_regla = db.Column(db.Numeric(10, 2), default=0.00)
    moneda = db.Column(db.String(10), default='USD') # USD, BCV, USDT, EURO
    activa = db.Column(db.Boolean, default=True)

class ProductoPrecios(db.Model):
    __tablename__ = 'producto_precios'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id', ondelete='CASCADE'), nullable=False)
    lista_id = db.Column(db.Integer, db.ForeignKey('listas_precios.id', ondelete='CASCADE'), nullable=False)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    
    producto = db.relationship('Productos', backref=db.backref('precios_alternativos', cascade='all, delete-orphan'))
    lista = db.relationship('ListasPrecios', backref='precios')
    
    __table_args__ = (db.UniqueConstraint('producto_id', 'lista_id', name='_producto_lista_uc'),)

# ==========================================
# CONFIGURACIÓN GENERAL DEL SISTEMA
# ==========================================
class Configuracion(db.Model):
    __tablename__ = 'configuracion'
    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.String(255), nullable=False)

# ==========================================
# MÓDULO DE COMPRAS
# ==========================================
class OrdenCompra(db.Model):
    __tablename__ = 'ordenes_compra'
    id = db.Column(db.Integer, primary_key=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('contactos.id'), nullable=False)
    referencia = db.Column(db.String(50), unique=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_recepcion = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(20), default='Borrador') # Borrador, En Tránsito, Recibida, Cancelada
    total = db.Column(db.Numeric(10, 2), default=0.00)
    observaciones = db.Column(db.Text, nullable=True)
    
    # CxP
    estado_pago = db.Column(db.String(20), nullable=False, default='Pagada')
    monto_abonado = db.Column(db.Numeric(10, 2), nullable=True, default=0.0)
    fecha_vencimiento = db.Column(db.DateTime, nullable=True)
    
    proveedor = db.relationship('Contactos', backref='ordenes_compra')
    detalles = db.relationship('DetalleOrdenCompra', backref='orden', lazy=True, cascade='all, delete-orphan')
    pagos = db.relationship('PagosCxP', backref='orden', lazy=True, cascade='all, delete-orphan')

class DetalleOrdenCompra(db.Model):
    __tablename__ = 'detalle_orden_compra'
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('ordenes_compra.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad_pedida = db.Column(db.Integer, nullable=False)
    cantidad_recibida = db.Column(db.Integer, default=0)
    costo_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    
    producto = db.relationship('Productos', backref='detalles_compra')

class Notificacion(db.Model):
    __tablename__ = 'notificaciones'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True) # Null si es global
    mensaje = db.Column(db.String(500), nullable=False)
    tipo = db.Column(db.String(50), default='info') # success, danger, info, warning
    leida = db.Column(db.Boolean, default=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)


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
    
    # Control de cuentas por pagar/cobrar
    pago_cliente_estado = db.Column(db.String(50), default='Pendiente') # Pendiente, Parcial, Pagado
    pago_proveedor_estado = db.Column(db.String(50), default='Pendiente') # Pendiente, Parcial, Pagado
    
    pago_cliente_monto = db.Column(db.Numeric(10, 2), nullable=True, default=0.00)
    pago_proveedor_monto = db.Column(db.Numeric(10, 2), nullable=True, default=0.00)
    pagos_proveedor = db.relationship('PagosDropshipping', backref='orden', lazy=True)

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

# ==========================================
# MÓDULO DE FINANZAS (CxC / CxP)
# ==========================================
class PagosCxC(db.Model):
    __tablename__ = 'pagos_cxc'
    id = db.Column(db.Integer, primary_key=True)
    guia_id = db.Column(db.Integer, db.ForeignKey('guias_despacho.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    metodo = db.Column(db.String(50), nullable=True)
    referencia_pago = db.Column(db.String(100), nullable=True)
    tasa_usada = db.Column(db.Numeric(10, 4), nullable=True)
    moneda_tasa = db.Column(db.String(20), nullable=True)
    monto_moneda = db.Column(db.Numeric(15, 2), nullable=True)

class PagosCxP(db.Model):
    __tablename__ = 'pagos_cxp'
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('ordenes_compra.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    metodo = db.Column(db.String(50), nullable=True)
    referencia_pago = db.Column(db.String(100), nullable=True)
    tasa_usada = db.Column(db.Numeric(10, 4), nullable=True)
    moneda_tasa = db.Column(db.String(20), nullable=True)
    monto_moneda = db.Column(db.Numeric(15, 2), nullable=True)


class PagosDropshipping(db.Model):
    __tablename__ = 'pagos_dropshipping'
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('ordenes_dropshipping.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    metodo = db.Column(db.String(50), nullable=True)
    referencia_pago = db.Column(db.String(100), nullable=True)
    tasa_usada = db.Column(db.Numeric(10, 4), nullable=True)
    moneda_tasa = db.Column(db.String(20), nullable=True)
    monto_moneda = db.Column(db.Numeric(15, 2), nullable=True)
