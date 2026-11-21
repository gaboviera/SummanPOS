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
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relación mágica con los atributos dinámicos
    valores = db.relationship('ValoresAtributos', secondary=productos_valores, lazy='subquery',
        backref=db.backref('productos', lazy=True))

    def __init__(self, nombre, cantidad, precio, descripcion=None, categoria_id=None):
        self.nombre = nombre
        self.cantidad = cantidad
        self.precio = precio
        self.descripcion = descripcion
        self.categoria_id = categoria_id

# ==========================================
# TASAS DE CAMBIO (BCV)
# ==========================================
class TasaCambio(db.Model):
    __tablename__ = 'tasa_cambio'
    id = db.Column(db.Integer, primary_key=True)
    # Guardamos solo un registro por día
    fecha = db.Column(db.Date, unique=True, nullable=False)
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
    
    # Datos Internos
    vendedor_nombre = db.Column(db.String(255), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    estado = db.Column(db.String(20), nullable=False, default='Completada')

class Contactos(db.Model):
    __tablename__ = 'contactos'
    id = db.Column(db.Integer, primary_key=True)
    identificacion = db.Column(db.String(50), unique=True, nullable=False) # RIF o CI
    nombre = db.Column(db.String(255), nullable=False)
    correo = db.Column(db.String(150), nullable=True, unique=True)
    direccion = db.Column(db.String(255), nullable=True)
    telefono = db.Column(db.String(50), nullable=True)
    tipo = db.Column(db.String(50), nullable=False, default='Cliente') # 'Cliente', 'Proveedor', 'Ambos', 'Contacto Usuario', 'Sin Definir'
    deleted_at = db.Column(db.DateTime, nullable=True)

