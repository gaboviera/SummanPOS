from flask import Blueprint, request, flash, redirect, url_for, render_template, jsonify
from flask_login import current_user, login_required
from utils.decorators import rol_requerido
from services.atributos_service import (
    guardar_atributo,
    eliminar_atributo,
    obtener_valores_por_atributo,
    guardar_valor_atributo,
    eliminar_valor_atributo
)
from extensions import db
from models import Atributos, ValoresAtributos
from forms import AtributosForm

atributos_bp = Blueprint("atributos", __name__)

def asegurar_atributo_marca():
    """Garantiza que el atributo Marca y todas sus marcas (valores) estén siempre activos y recuperados."""
    try:
        marca = Atributos.query.filter(Atributos.nombre.ilike("marca")).first()
        if marca:
            hubo_cambios = False
            if marca.deleted_at is not None:
                marca.deleted_at = None
                hubo_cambios = True

            val_recuperados = ValoresAtributos.query.filter(
                ValoresAtributos.atributo_id == marca.id,
                ValoresAtributos.deleted_at.isnot(None)
            ).update({"deleted_at": None}, synchronize_session=False)

            if val_recuperados > 0 or hubo_cambios:
                db.session.commit()
    except Exception:
        db.session.rollback()

@atributos_bp.before_request
def requerir_login():
    if not current_user.is_authenticated:
        flash("Debes iniciar sesión para acceder a esta página.", "warning")
        return redirect(url_for('auth.login'))

@atributos_bp.route("/atributos", methods=["GET"])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def index():
    asegurar_atributo_marca()

    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    # Filtrar únicamente los atributos activos para que los eliminados no aparezcan
    query = Atributos.query.filter_by(deleted_at=None)

    if q:
        query = query.filter(Atributos.nombre.ilike(f'%{q}%'))
        
    atributos_paginados = query.order_by(Atributos.nombre.asc()).paginate(page=page, per_page=15, error_out=False)
    
    form = AtributosForm()
    
    return render_template("atributos.html", atributos=atributos_paginados, q=q, form=form)

@atributos_bp.route("/atributos/guardar", methods=["POST"])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def route_guardar_atributo():
    form = AtributosForm()
    if form.validate_on_submit():
        try:
            guardar_atributo(
                atributo_id=form.atributo_id.data,
                nombre=form.nombre.data
            )
            flash("Atributo guardado con éxito.", "success")
        except ValueError as e:
            flash(str(e), "warning")
        except Exception as e:
            flash(f"Error inesperado al guardar: {str(e)}", "danger")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en {getattr(form, field).label.text}: {error}", "danger")
        
    return redirect(url_for("atributos.index"))

@atributos_bp.route("/atributos/eliminar/<int:id>", methods=["POST"])
@login_required
@rol_requerido('Administrador')
def route_eliminar_atributo(id):
    try:
        attr = Atributos.query.get(id)
        if attr and attr.nombre.strip().lower() == 'marca':
            flash("El atributo 'Marca' no se puede eliminar por ser parte esencial del sistema.", "warning")
            return redirect(url_for("atributos.index"))

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
