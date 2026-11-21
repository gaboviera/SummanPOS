import os   
from flask import Flask 
from dotenv import load_dotenv
from extensions import db, migrate, bcrypt, login_manager
from flask_apscheduler import APScheduler

# Inicializamos el motor del Cron
scheduler = APScheduler()

def create_app():
    # Cargar variables de entorno desde tu archivo .env
    load_dotenv()

    app = Flask(__name__)

    # 1. Configuración de seguridad y base de datos
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret")

    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")

    # Construimos la URL de conexión a PostgreSQL
    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # 2. Inicializamos las extensiones con nuestra app
    db.init_app(app)  # <-- Corregido: un solo guion bajo
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.init_app(app)

    # IMPORTAMOS LOS MODELOS AQUÍ para que la base de datos los reconozca
    with app.app_context():
        import models

    # 3. Registrar Blueprints
    from routes.inventario_routes import inventario_bp
    from routes.contactos_routes import contactos_bp
    from routes.atributos_routes import atributos_bp
    from routes.auth_routes import auth_bp
    from routes.usuarios_routes import usuarios_bp
    from routes.categorias_routes import categorias_bp
    from routes.ventas_routes import ventas_bp
    
    app.register_blueprint(inventario_bp)
    app.register_blueprint(contactos_bp)
    app.register_blueprint(atributos_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(categorias_bp)
    app.register_blueprint(ventas_bp)

    # --- CONFIGURACIÓN DEL CRON BCV (Odoo style) ---
    app.config['SCHEDULER_API_ENABLED'] = False
    
    from services.bcv_service import actualizar_tasa_bcv
    
    # Programamos que la tasa se actualice sola todos los días a las 8:00 AM
    @scheduler.task('cron', id='actualizar_bcv', hour=8, minute=0)
    def tarea_programada_bcv():
        actualizar_tasa_bcv(app=app)
        
    # Evitar error si Flask recarga el código en modo debug
    if not scheduler.running:
        try:
            scheduler.init_app(app)
            scheduler.start()
        except Exception:
            pass

    return app

def crear_usuario_admin_si_no_existe(app):
    from models import Rol, Usuario
    from services.auth_services import encriptar_password
    with app.app_context():
        db.create_all() # Asegura que las tablas existan
        
        # 1. Crear Roles si no existen
        rol_admin = Rol.query.filter_by(nombre="Administrador").first()
        if not rol_admin:
            rol_admin = Rol(nombre="Administrador")
            db.session.add(rol_admin)
            
        # Si ya existe "Cajero" o "Usuario Normal", lo renombramos a "Usuario" para migrar los datos viejos
        rol_viejo = Rol.query.filter(Rol.nombre.in_(["Cajero", "Usuario Normal"])).first()
        if rol_viejo:
            rol_viejo.nombre = "Usuario"
            
        rol_usuario = Rol.query.filter_by(nombre="Usuario").first()
        if not rol_usuario:
            rol_usuario = Rol(nombre="Usuario")
            db.session.add(rol_usuario)
            
        db.session.commit()
            
        # 2. Crear Usuario admin si no existe ninguno en el sistema
        if Usuario.query.count() == 0:
            usuario_admin = Usuario(
                username="admin",
                password_hash=encriptar_password("admin123"),
                rol_id=rol_admin.id
            )
            db.session.add(usuario_admin)
            db.session.commit()
            print("==================================================")
            print("🛡️  SISTEMA DE SEGURIDAD ACTIVADO")
            print("Usuario por defecto creado:")
            print("Username: admin")
            print("Password: admin123")
            print("==================================================")

# ESTO ES CRÍTICO: Debe estar pegado al margen izquierdo
app = create_app()
crear_usuario_admin_si_no_existe(app)

if __name__ == '__main__':
    # Arrancamos en modo debug solo para desarrollo local
    app.run(debug=True)
