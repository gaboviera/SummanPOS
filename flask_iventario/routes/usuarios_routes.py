from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from services.usuarios_service import guardar_usuario, eliminar_usuario, obtener_todos_roles
from utils.decorators import rol_requerido
from extensions import db
from models import Usuario
from functools import wraps
from forms import UsuariosForm

usuarios_bp = Blueprint("usuarios", __name__)

@usuarios_bp.route("/usuarios", methods=["GET"])
@login_required
@rol_requerido('Administrador')
def index():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    query = Usuario.query

    if q:
        query = query.filter(Usuario.username.ilike(f'%{q}%'))
        
    usuarios_paginados = query.order_by(Usuario.username.asc()).paginate(page=page, per_page=15, error_out=False)
    roles = obtener_todos_roles()
    
    form = UsuariosForm()
    form.rol_id.choices = [(r.id, r.nombre) for r in roles]
    
    return render_template("usuarios.html", usuarios=usuarios_paginados, roles=roles, q=q, form=form)

@usuarios_bp.route("/usuarios/guardar", methods=["POST"])
@login_required
@rol_requerido('Administrador')
def route_guardar_usuario():
    form = UsuariosForm()
    form.rol_id.choices = [(r.id, r.nombre) for r in obtener_todos_roles()]
    
    # Excluir validación de contraseña si estamos editando y no se envió nueva contraseña
    if form.usuario_id.data and not form.password.data:
        from wtforms.validators import Optional
        form.password.validators = [Optional()]
        
    if form.validate_on_submit():
        try:
            guardar_usuario(
                usuario_id=form.usuario_id.data,
                username=form.username.data,
                password=form.password.data,
                rol_id=form.rol_id.data,
                activo=form.activo.data
            )
            flash("Usuario guardado con éxito.", "success")
        except ValueError as e:
            flash(str(e), "warning")
        except Exception as e:
            flash(f"Error inesperado al guardar: {str(e)}", "danger")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{error}", "danger")
        
    return redirect(url_for("usuarios.index"))

@usuarios_bp.route("/usuarios/eliminar/<int:id>", methods=["POST"])
@login_required
@rol_requerido('Administrador')
def route_eliminar_usuario(id):
    try:
        eliminar_usuario(id)
        flash("Usuario eliminado con éxito.", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Error al eliminar usuario: {str(e)}", "danger")
        
    return redirect(url_for("usuarios.index"))
