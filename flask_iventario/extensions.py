from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager


# Aquí solo instanciamos las extensiones sin asociarlas a la app todavía.
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()

# Pequeña configuración de seguridad para redireccionar a los usuarios que no han iniciado sesión
login_manager.login_view = "auth.login"
login_manager.login_message = "por favor inicie session para acceder a esta pagina."
login_manager.login_message_category = "info"



