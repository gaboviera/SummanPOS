import sys
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

    db_user = os.getenv("PGUSER", os.getenv("DB_USER"))
    db_password = os.getenv("PGPASSWORD", os.getenv("DB_PASSWORD"))
    db_host = os.getenv("PGHOST", os.getenv("DB_HOST", "localhost"))
    db_port = os.getenv("PGPORT", os.getenv("DB_PORT", "5432"))
    db_name = os.getenv("PGDATABASE", os.getenv("DB_NAME"))

    import urllib.parse
    db_password_encoded = urllib.parse.quote_plus(db_password) if db_password else ""

    # Construimos la URL de conexión a PostgreSQL
    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{db_user}:{db_password_encoded}@{db_host}:{db_port}/{db_name}"
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
    from routes.compras_routes import compras_bp
    from routes.bcv_routes import bcv_bp
    from routes.configuracion_routes import config_bp
    from routes.notificaciones_routes import notificaciones_bp
    from routes.dropshipping_routes import dropshipping_bp
    from routes.finanzas_routes import finanzas_bp

    app.register_blueprint(inventario_bp)
    app.register_blueprint(contactos_bp)
    app.register_blueprint(atributos_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(categorias_bp)
    app.register_blueprint(notificaciones_bp)
    app.register_blueprint(ventas_bp)
    app.register_blueprint(compras_bp)
    app.register_blueprint(dropshipping_bp)
    app.register_blueprint(finanzas_bp)
    app.register_blueprint(bcv_bp)
    app.register_blueprint(config_bp)

    # --- CONFIGURACIÓN DEL CRON BCV (Odoo style) ---
    app.config['SCHEDULER_API_ENABLED'] = False
    app.config['SCHEDULER_JOBSTORES'] = {'default': {'type': 'memory'}}
    
    from services.bcv_service import actualizar_tasa_bcv
    from services.binance_service import actualizar_tasa_usdt
    
    # Programamos que la tasa se actualice sola todos los días a las 8:00 AM
    @scheduler.task('cron', id='actualizar_bcv', hour=8, minute=0)
    def tarea_programada_bcv():
        actualizar_tasa_bcv(app=app)

    # Programamos que la tasa USDT se actualice cada 4 horas
    @scheduler.task('interval', id='actualizar_usdt', hours=4)
    def tarea_programada_usdt():
        actualizar_tasa_usdt(app=app)
        
    # Programamos limpieza de PDFs antiguos (se ejecuta una vez al día a las 2 AM)
    @scheduler.task('cron', id='limpiar_pdfs', hour=2, minute=0)
    def tarea_programada_limpiar_pdfs():
        from services.limpieza_service import limpiar_pdfs_antiguos
        limpiar_pdfs_antiguos(app=app)
        
    # Usar fcntl para asegurar que el scheduler solo corra en 1 worker
    import platform
    if not scheduler.running:
        if platform.system() != 'Windows':
            import fcntl
            import atexit
            try:
                # Intentamos adquirir un lock exclusivo no bloqueante
                f = open("scheduler.lock", "w")
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                scheduler.init_app(app)
                scheduler.start()
                # Mantener el lock activo hasta que el proceso termine
                atexit.register(lambda: f.close())
            except Exception:
                # Si no logramos adquirir el lock (ya está en uso por otro worker), ignoramos
                pass
        else:
            # Fallback para desarrollo en Windows (donde fcntl no existe)
            try:
                scheduler.init_app(app)
                scheduler.start()
            except Exception:
                pass
            
    # --- CONTEXTO GLOBAL PARA PLANTILLAS ---
    @app.context_processor
    def inject_global_vars():
        from models import Configuracion, Notificacion
        from flask_login import current_user
        from flask import has_request_context
        
        conf_logo = Configuracion.query.filter_by(clave="logo_url").first()
        conf_fav = Configuracion.query.filter_by(clave="favicon_url").first()
        
        notificaciones_no_leidas = []
        if has_request_context() and getattr(current_user, 'is_authenticated', False):
            notificaciones_no_leidas = Notificacion.query.filter(
                (Notificacion.usuario_id == current_user.id) | (Notificacion.usuario_id == None),
                Notificacion.leida == False
            ).order_by(Notificacion.fecha.desc()).all()
            
        from models import TasaCambio
        t_euro = TasaCambio.query.filter_by(fuente='BCV_EURO').order_by(TasaCambio.id.desc()).first()
        tasa_euro_global = float(t_euro.tasa) if t_euro else 974.4191

        conf_ds = Configuracion.query.filter_by(clave="modulo_dropshipping_activo").first()
        modulo_dropshipping_activo = (conf_ds.valor.lower() in ['true', '1', 'si']) if conf_ds else False

        return dict(
            brand_logo_url=conf_logo.valor if conf_logo else None,
            brand_favicon_url=conf_fav.valor if conf_fav else None,
            notificaciones_no_leidas=notificaciones_no_leidas,
            tasa_euro_global=tasa_euro_global,
            modulo_dropshipping_activo=modulo_dropshipping_activo
        )

    return app

def crear_usuario_admin_si_no_existe(app):
    """Siembra roles y el usuario admin inicial.

    NO crea tablas. El esquema lo construyen exclusivamente las migraciones
    de Alembic ('flask db upgrade'). Si las tablas todavia no existen, la
    siembra se omite y se avisa, en vez de fallar en silencio.
    """
    from sqlalchemy import inspect
    from models import Rol, Usuario
    from services.auth_services import encriptar_password

    with app.app_context():
        if not inspect(db.engine).has_table("roles"):
            app.logger.warning(
                "Las tablas no existen todavia. Ejecuta 'flask db upgrade' "
                "antes de arrancar la aplicacion. Siembra inicial omitida."
            )
            return

        try:
            # 1. Crear Roles si no existen
            roles_requeridos = ["Super Admin", "Administrador", "Supervisor", "Cajero"]
            for nombre_rol in roles_requeridos:
                if not Rol.query.filter_by(nombre=nombre_rol).first():
                    db.session.add(Rol(nombre=nombre_rol))
            db.session.commit()  # Guardar roles primero

            # 2. Migrar usuarios viejos a Cajero
            rol_cajero = Rol.query.filter_by(nombre="Cajero").first()
            if rol_cajero:
                roles_viejos = Rol.query.filter(Rol.nombre.in_(["Usuario", "Usuario Normal"])).all()
                for rol_v in roles_viejos:
                    # Reasignar rol_id usando update masivo para evitar que el ORM asigne NULL
                    Usuario.query.filter_by(rol_id=rol_v.id).update({"rol_id": rol_cajero.id})
                    db.session.delete(rol_v)

                db.session.commit()

            # 3. Crear Usuario admin si no existe ninguno en el sistema
            if Usuario.query.count() == 0:
                rol_admin = Rol.query.filter_by(nombre="Administrador").first()
                if rol_admin:
                    usuario_admin = Usuario(
                        username="admin",
                        password_hash=encriptar_password("admin123"),
                        rol_id=rol_admin.id
                    )
                    db.session.add(usuario_admin)
                    db.session.commit()
                    print("==================================================")
                    print("SISTEMA DE SEGURIDAD ACTIVADO")
                    print("Usuario por defecto creado:")
                    print("Username: admin")
                    print("Password: admin123")
                    print("==================================================")

            # 3.1 Asignar rol Super Admin al usuario admin principal
            rol_super = Rol.query.filter_by(nombre="Super Admin").first()
            user_admin = Usuario.query.filter_by(username="admin").first()
            if user_admin and rol_super and user_admin.rol_id != rol_super.id:
                user_admin.rol_id = rol_super.id
                db.session.commit()

            # 4. Asegurar configuracion de dropshipping desactivada y productos en inventario fisico estandar
            if inspect(db.engine).has_table("configuracion"):
                from models import Configuracion
                conf_ds = Configuracion.query.filter_by(clave="modulo_dropshipping_activo").first()
                if not conf_ds:
                    db.session.add(Configuracion(clave="modulo_dropshipping_activo", valor="false"))
                    db.session.commit()

            if inspect(db.engine).has_table("productos"):
                from models import Productos
                Productos.query.filter_by(es_dropshipping=True).update({"es_dropshipping": False})
                db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Fallo la siembra de datos iniciales")


def _debe_sembrar():
    """La siembra no debe correr durante los comandos de Alembic.

    Con FLASK_APP=app.py, este modulo se importa antes de ejecutar cualquier
    'flask db ...'. Si la siembra corriera ahi, tocaria la base justo cuando
    Alembic esta a punto de modificarla.
    """
    if os.getenv("SKIP_DB_BOOTSTRAP", "").strip().lower() in ("1", "true", "yes"):
        return False
    return sys.argv[1:2] not in (["db"], ["seed-inicial"])


# ESTO ES CRITICO: Debe estar pegado al margen izquierdo
app = create_app()

if _debe_sembrar():
    crear_usuario_admin_si_no_existe(app)


@app.cli.command("seed-inicial")
def seed_inicial_command():
    """Siembra roles y el usuario admin. Ejecutar DESPUES de 'flask db upgrade'."""
    crear_usuario_admin_si_no_existe(app)

if __name__ == '__main__':
    # Arrancamos en modo debug solo para desarrollo local
    app.run(debug=True)
