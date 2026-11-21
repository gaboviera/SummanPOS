from flask import Blueprint, request, flash, redirect, url_for, render_template, jsonify
from flask_login import current_user
from services.contactos_service import (
    obtener_todos_contactos,
    obtener_lista_diccionarios_contactos,
    guardar_contacto,
    eliminar_contacto
)

contactos_bp = Blueprint("contactos", __name__)

@contactos_bp.before_request
def requerir_login():
    if not current_user.is_authenticated:
        if request.path.startswith("/api/"):
            return jsonify({"error": "No autorizado"}), 401
        flash("Debes iniciar sesión para acceder a esta página.", "warning")
        return redirect(url_for('auth.login'))

@contactos_bp.route("/contactos", methods=["GET"])
def index():
    tipo_filtro = request.args.get("tipo", "").strip()
    lista_contactos = obtener_todos_contactos(tipo=tipo_filtro if tipo_filtro else None)
    return render_template("contactos.html", contactos=lista_contactos, tipo_filtro=tipo_filtro)

@contactos_bp.route("/api/contactos", methods=["GET"])
def api_contactos():
    tipo = request.args.get("tipo", "").strip()
    solo_clientes = (tipo.lower() == 'cliente') if tipo else False
    contactos = obtener_lista_diccionarios_contactos(tipo=tipo if tipo else None, solo_clientes=solo_clientes)
    return jsonify(contactos)

@contactos_bp.route("/contactos/guardar", methods=["POST"])
def route_guardar_contacto():
    try:
        guardar_contacto(
            contacto_id=request.form.get("contacto_id"),
            identificacion=request.form.get("identificacion"),
            nombre=request.form.get("nombre"),
            correo=request.form.get("correo"),
            direccion=request.form.get("direccion"),
            telefono=request.form.get("telefono"),
            tipo=request.form.get("tipo", "Cliente")
        )
        flash("Contacto guardado con éxito.", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Error inesperado al guardar: {str(e)}", "danger")
        
    return redirect(url_for("contactos.index"))

@contactos_bp.route("/contactos/generar_usuario/<int:id>", methods=["POST"])
def route_generar_usuario(id):
    if current_user.rol.nombre != 'Administrador':
        flash("Acceso denegado.", "danger")
        return redirect(url_for("contactos.index"))
        
    from models import Contactos, Rol
    from services.usuarios_service import guardar_usuario
    
    contacto = Contactos.query.get(id)
    if not contacto or not contacto.correo:
        flash("El contacto no existe o no tiene un correo configurado.", "danger")
        return redirect(url_for("contactos.index"))
        
    try:
        rol_cajero = Rol.query.filter_by(nombre="Usuario").first()
        if not rol_cajero:
            raise ValueError("El rol 'Usuario' no existe en el sistema.")
            
        guardar_usuario(
            usuario_id=None,
            username=contacto.correo.lower(),
            password="123456",
            rol_id=rol_cajero.id,
            activo=True
        )
        flash(f"Usuario {contacto.correo} generado con éxito. Su clave es 123456", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Error al generar usuario: {str(e)}", "danger")
        
    return redirect(url_for("contactos.index"))

@contactos_bp.route("/contactos/eliminar/<int:id>", methods=["POST"])
def route_eliminar_contacto(id):
    try:
        eliminar_contacto(id)
        flash("Contacto eliminado con éxito.", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Error al eliminar (posiblemente esté asociado a una venta): {str(e)}", "danger")
        
    return redirect(url_for("contactos.index"))
