from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_login import current_user
from services.atributos_service import obtener_todos_atributos, guardar_atributo, eliminar_atributo

atributos_bp = Blueprint("atributos", __name__)

@atributos_bp.before_request
def requerir_login():
    if not current_user.is_authenticated:
        flash("Debes iniciar sesión para acceder a esta página.", "warning")
        return redirect(url_for('auth.login'))

@atributos_bp.route("/atributos", methods=["GET"])
def index():
    lista_atributos = obtener_todos_atributos()
    return render_template("atributos.html", atributos=lista_atributos)

@atributos_bp.route("/atributos/guardar", methods=["POST"])
def route_guardar_atributo():
    try:
        guardar_atributo(
            atributo_id=request.form.get("atributo_id"),
            nombre=request.form.get("nombre")
        )
        flash("Atributo guardado con éxito.", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Error inesperado al guardar: {str(e)}", "danger")
        
    return redirect(url_for("atributos.index"))

@atributos_bp.route("/atributos/eliminar/<int:id>", methods=["POST"])
def route_eliminar_atributo(id):
    try:
        eliminar_atributo(id)
        flash("Atributo eliminado con éxito.", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Error al eliminar (posiblemente esté siendo usado por algún producto): {str(e)}", "danger")
        
    return redirect(url_for("atributos.index"))

# ==========================================
# RUTAS API PARA VALORES DE ATRIBUTOS (AJAX)
# ==========================================
from flask import jsonify
from services.atributos_service import obtener_valores_por_atributo, guardar_valor_atributo, eliminar_valor_atributo

@atributos_bp.route("/api/atributos/<int:atributo_id>/valores", methods=["GET"])
def api_obtener_valores(atributo_id):
    valores = obtener_valores_por_atributo(atributo_id)
    return jsonify({"success": True, "valores": valores})

@atributos_bp.route("/api/atributos/<int:atributo_id>/valores", methods=["POST"])
def api_guardar_valor(atributo_id):
    try:
        data = request.get_json()
        nuevo_valor = guardar_valor_atributo(atributo_id, data.get("valor"))
        return jsonify({"success": True, "valor": nuevo_valor})
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": "Error en el servidor"}), 500

@atributos_bp.route("/api/valores/<int:valor_id>", methods=["DELETE"])
def api_eliminar_valor(valor_id):
    try:
        eliminar_valor_atributo(valor_id)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": "Error al eliminar, posiblemente esté en uso."}), 500
