from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from extensions import db
from models import Notificacion

notificaciones_bp = Blueprint('notificaciones', __name__)

@notificaciones_bp.route("/api/notificaciones/marcar_leidas", methods=["POST"])
@login_required
def marcar_leidas():
    try:
        notificaciones = Notificacion.query.filter(
            (Notificacion.usuario_id == current_user.id) | (Notificacion.usuario_id == None),
            Notificacion.leida == False
        ).all()
        for notif in notificaciones:
            notif.leida = True
        db.session.commit()
        return jsonify({"success": True, "mensaje": "Notificaciones marcadas como leídas"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "mensaje": str(e)}), 500

@notificaciones_bp.route("/api/notificaciones/nuevas", methods=["GET"])
@login_required
def nuevas():
    try:
        notificaciones = Notificacion.query.filter(
            (Notificacion.usuario_id == current_user.id) | (Notificacion.usuario_id == None),
            Notificacion.leida == False
        ).order_by(Notificacion.fecha.desc()).all()
        datos = []
        for n in notificaciones:
            datos.append({
                "id": n.id,
                "mensaje": n.mensaje,
                "tipo": n.tipo,
                "fecha": n.fecha.strftime('%d-%m-%Y %H:%M')
            })
        return jsonify({"success": True, "notificaciones": datos})
    except Exception as e:
        return jsonify({"success": False, "mensaje": str(e)}), 500

@notificaciones_bp.route("/notificaciones")
@login_required
def historial():
    notificaciones = Notificacion.query.filter(
        (Notificacion.usuario_id == current_user.id) | (Notificacion.usuario_id == None)
    ).order_by(Notificacion.fecha.desc()).limit(50).all()
    return render_template("historial_notificaciones.html", notificaciones=notificaciones)
