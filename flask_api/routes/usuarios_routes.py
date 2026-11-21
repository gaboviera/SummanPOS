from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from services.usuarios_service import obtener_todos_usuarios, obtener_todos_roles, guardar_usuario, eliminar_usuario
from functools import wraps

usuarios_bp = Blueprint("usuarios", __name__)

def requerir_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol.nombre != "Administrador":
            flash("Acceso denegado. Se requieren permisos de Administrador.", "danger")
            return redirect(url_for('inventario.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@usuarios_bp.route("/usuarios", methods=["GET"])
@login_required
@requerir_admin
def index():
    usuarios = obtener_todos_usuarios()
    roles = obtener_todos_roles()
    return render_template("usuarios.html", usuarios=usuarios, roles=roles)

@usuarios_bp.route("/usuarios/guardar", methods=["POST"])
@login_required
@requerir_admin
def route_guardar_usuario():
    try:
        guardar_usuario(
            usuario_id=request.form.get("usuario_id"),
            username=request.form.get("username"),
            password=request.form.get("password"),
            rol_id=request.form.get("rol_id"),
            activo=request.form.get("activo") == "on"
        )
        flash("Usuario guardado con éxito.", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Error inesperado al guardar: {str(e)}", "danger")
        
    return redirect(url_for("usuarios.index"))

@usuarios_bp.route("/usuarios/eliminar/<int:id>", methods=["POST"])
@login_required
@requerir_admin
def route_eliminar_usuario(id):
    try:
        eliminar_usuario(id)
        flash("Usuario eliminado con éxito.", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Error al eliminar usuario: {str(e)}", "danger")
        
    return redirect(url_for("usuarios.index"))
