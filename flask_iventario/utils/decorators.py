from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def rol_requerido(*roles_permitidos):
    """
    Decorador para restringir el acceso a ciertas vistas basado en el rol del usuario.
    Ejemplo de uso: @rol_requerido('Administrador', 'Supervisor')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Por favor, inicia sesión para acceder a esta página.", "warning")
                return redirect(url_for('auth.login'))
            
            # Super Admin tiene acceso total a cualquier vista protegida
            if current_user.rol and current_user.rol.nombre == 'Super Admin':
                return f(*args, **kwargs)

            # Verificar si el nombre del rol del usuario está en la lista de permitidos
            if not current_user.rol or current_user.rol.nombre not in roles_permitidos:
                flash("Acceso Denegado. No tienes los permisos necesarios para realizar esta acción.", "danger")
                return redirect(url_for('inventario.dashboard'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
