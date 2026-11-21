from flask import Blueprint, jsonify, request, redirect, url_for, flash, render_template
from flask_login import login_required
from services.bcv_service import actualizar_tasa_bcv
from services.binance_service import actualizar_tasa_usdt
from models import TasaCambio
from datetime import datetime
from sqlalchemy import func
from extensions import db

bcv_bp = Blueprint('bcv', __name__, url_prefix='/bcv')

@bcv_bp.route('/actualizar', methods=['GET', 'POST'])
@login_required
def actualizar():
    success, msg = actualizar_tasa_bcv()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({"success": success, "message": msg})
        
    flash(msg, "success" if success else "danger")
    return redirect(request.referrer or url_for('inventario.dashboard'))

@bcv_bp.route('/actualizar_usdt', methods=['GET', 'POST'])
@login_required
def actualizar_usdt():
    success, msg = actualizar_tasa_usdt()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({"success": success, "message": msg})
        
    flash(msg, "success" if success else "danger")
    return redirect(request.referrer or url_for('inventario.dashboard'))

@bcv_bp.route('/historial', methods=['GET'])
@login_required
def historial_tasas():
    page = request.args.get('page', 1, type=int)
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()
    fuente = request.args.get('fuente', '').strip()
    
    query = TasaCambio.query

    if fecha_inicio:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            query = query.filter(func.date(TasaCambio.fecha) >= fecha_inicio_dt.date())
        except ValueError:
            pass

    if fecha_fin:
        try:
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            query = query.filter(func.date(TasaCambio.fecha) <= fecha_fin_dt.date())
        except ValueError:
            pass
            
    if fuente:
        query = query.filter(TasaCambio.fuente == fuente)
        
    tasas = query.order_by(TasaCambio.id.desc(), TasaCambio.fuente.asc()).paginate(page=page, per_page=30, error_out=False)
    
    return render_template('historial_tasas.html', tasas=tasas, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, fuente=fuente)

@bcv_bp.route('/manual', methods=['POST'])
@login_required
def fijar_tasa_manual():
    fuente = request.form.get('fuente', '').strip()
    tasa_val = request.form.get('tasa', type=float)
    
    if not fuente or not tasa_val or tasa_val <= 0:
        flash("Monto o tipo de tasa inválido.", "danger")
        return redirect(request.referrer or url_for('inventario.dashboard'))
    
    nueva = TasaCambio(fecha=datetime.now(), tasa=tasa_val, fuente=fuente)
    db.session.add(nueva)
    db.session.commit()
    
    nombre_fuente = "Euro BCV" if fuente == 'BCV_EURO' else ("USDT" if fuente == 'BINANCE_USDT' else "Dólar BCV")
    flash(f"Tasa {nombre_fuente} fijada manualmente a {tasa_val:,.2f} Bs.", "success")
    return redirect(request.referrer or url_for('bcv.historial_tasas'))


@bcv_bp.route('/actualizar_euro', methods=['GET', 'POST'])
@login_required
def actualizar_euro_bcv():
    from services.bcv_service import actualizar_tasa_euro_bcv
    ok, msg = actualizar_tasa_euro_bcv()
    flash(msg, "success" if ok else "danger")
    return redirect(request.referrer or url_for('inventario.dashboard'))
