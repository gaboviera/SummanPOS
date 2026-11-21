from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from datetime import datetime, timedelta
from utils.decorators import rol_requerido
from extensions import db
from services.finanzas_service import (
    obtener_tasas_cambio, 
    obtener_cxc, 
    registrar_abono_cxc as srv_registrar_abono_cxc,
    obtener_cxp, 
    registrar_abono_cxp as srv_registrar_abono_cxp,
    cxp_abonar_drop as srv_cxp_abonar_drop,
    obtener_historial_pagos
)

finanzas_bp = Blueprint('finanzas', __name__, url_prefix='/finanzas')

class CustomPagination:
    def __init__(self, page, per_page, total, items):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.items = items
        self.pages = (total + per_page - 1) // per_page if per_page else 0
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1
        self.next_num = page + 1
        
    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num



def sanitizar_decimal(val, default=None):
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    if not val_str:
        return default
    if '.' in val_str and ',' in val_str:
        if val_str.rfind(',') > val_str.rfind('.'):
            val_str = val_str.replace('.', '').replace(',', '.')
        else:
            val_str = val_str.replace(',', '')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return default

_columnas_verificadas = False

def asegurar_columnas_pagos():
    global _columnas_verificadas
    if _columnas_verificadas:
        return
    from extensions import db
    from sqlalchemy import text
    sentencias = [
        "ALTER TABLE pagos_cxc ADD COLUMN IF NOT EXISTS tasa_usada NUMERIC(10, 4);",
        "ALTER TABLE pagos_cxc ADD COLUMN IF NOT EXISTS moneda_tasa VARCHAR(20);",
        "ALTER TABLE pagos_cxc ADD COLUMN IF NOT EXISTS monto_moneda NUMERIC(15, 2);",
        "ALTER TABLE pagos_cxp ADD COLUMN IF NOT EXISTS tasa_usada NUMERIC(10, 4);",
        "ALTER TABLE pagos_cxp ADD COLUMN IF NOT EXISTS moneda_tasa VARCHAR(20);",
        "ALTER TABLE pagos_cxp ADD COLUMN IF NOT EXISTS monto_moneda NUMERIC(15, 2);",
        "ALTER TABLE pagos_dropshipping ADD COLUMN IF NOT EXISTS tasa_usada NUMERIC(10, 4);",
        "ALTER TABLE pagos_dropshipping ADD COLUMN IF NOT EXISTS moneda_tasa VARCHAR(20);",
        "ALTER TABLE pagos_dropshipping ADD COLUMN IF NOT EXISTS monto_moneda NUMERIC(15, 2);"
    ]
    for sql in sentencias:
        try:
            db.session.execute(text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()
    _columnas_verificadas = True

@finanzas_bp.route('/cxc', methods=['GET'])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def cuentas_por_cobrar():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()
    estado = request.args.get('estado', 'pendientes').strip()
    
    guias_credito = obtener_cxc(request.args)
    tasas = obtener_tasas_cambio()
    
    lista_cxc = []
    total_por_cobrar_usd = 0.0
    hoy = datetime.utcnow() - timedelta(hours=4)

    for g in guias_credito:
        total_venta_usd = round(float(g.total), 2)
        monto_abonado_usd = float(g.monto_abonado or 0.0)
        saldo_pendiente_usd = max(0.0, total_venta_usd - monto_abonado_usd)
        
        if estado in ['pendientes', 'parciales'] and saldo_pendiente_usd <= 0.01:
            continue
        if estado == 'pagadas' and saldo_pendiente_usd > 0.01:
            continue
        
        total_por_cobrar_usd += saldo_pendiente_usd
        dias_transcurridos = (hoy - g.fecha).days if g.fecha else 0
        
        dias_vencido = 0
        if g.fecha_vencimiento and hoy > g.fecha_vencimiento:
            dias_vencido = (hoy - g.fecha_vencimiento).days

        lista_cxc.append({
            'id': g.id,
            'referencia': g.referencia,
            'fecha': g.fecha - timedelta(hours=4) if g.fecha else None,
            'cliente_nombre': g.cliente_nombre,
            'cliente_telefono': g.cliente_telefono,
            'cliente_identificacion': g.cliente_identificacion,
            'total_venta_usd': total_venta_usd,
            'monto_abonado_usd': monto_abonado_usd,
            'saldo_pendiente_usd': saldo_pendiente_usd,
            'porcentaje_pagado': min(100.0, round((monto_abonado_usd / total_venta_usd) * 100, 1)) if total_venta_usd > 0 else 0,
            'fecha_vencimiento': g.fecha_vencimiento - timedelta(hours=4) if g.fecha_vencimiento else None,
            'dias_transcurridos': dias_transcurridos,
            'dias_vencido': dias_vencido,
            'estado_pago': g.estado_pago,
            'pagos': g.pagos
        })

    total_items = len(lista_cxc)
    per_page = 20
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginacion = CustomPagination(page, per_page, total_items, lista_cxc[start_idx:end_idx])

    return render_template(
        'finanzas/cxc.html',
        paginacion=paginacion,
        lista_cxc=paginacion.items,
        total_por_cobrar_usd=total_por_cobrar_usd,
        tasa_bcv=tasas['bcv'],
        tasa_euro=tasas['euro'],
        tasa_usdt=tasas['usdt'],
        q=q,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        estado=estado
    )

@finanzas_bp.route('/cxc/abono/<int:guia_id>', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def registrar_abono_cxc(guia_id):
    asegurar_columnas_pagos()
    monto = sanitizar_decimal(request.form.get('monto'), default=0.0)
    metodo = request.form.get('metodo', 'Efectivo USD')
    referencia_pago = request.form.get('referencia_pago', '')
    tasa_raw = request.form.get('tasa_usada')
    moneda_tasa = request.form.get('moneda_tasa')
    monto_moneda_raw = request.form.get('monto_moneda')
    
    if monto <= 0:
        flash("El monto del abono debe ser mayor a 0.", "danger")
        return redirect(url_for('finanzas.cuentas_por_cobrar'))

    tasa_usada = sanitizar_decimal(tasa_raw, default=None)
    monto_moneda = sanitizar_decimal(monto_moneda_raw, default=None)

    if tasa_usada and tasa_usada > 0:
        tasa_usada = round(tasa_usada, 4)
        if not monto_moneda or monto_moneda <= 0:
            monto_moneda = round(monto * tasa_usada, 2)
        else:
            monto_moneda = round(monto_moneda, 2)

        if not moneda_tasa or moneda_tasa in ['BCV', 'Tasa']:
            if 'USDT' in metodo or 'Binance' in metodo:
                moneda_tasa = 'USDT'
            elif 'EUR' in metodo or 'Euro' in metodo:
                moneda_tasa = 'EUR'
            else:
                moneda_tasa = 'BCV'
    else:
        tasa_usada = None
        monto_moneda = None
            
    exito, mensaje = srv_registrar_abono_cxc(guia_id, monto, metodo, referencia_pago, tasa_usada, moneda_tasa, monto_moneda)
    
    if exito and tasa_usada:
        from models import PagosCxC
        ultimo_pago = PagosCxC.query.filter_by(guia_id=guia_id).order_by(PagosCxC.id.desc()).first()
        if ultimo_pago:
            ultimo_pago.moneda_tasa = moneda_tasa
            ultimo_pago.monto_moneda = monto_moneda
            db.session.commit()
    
    if exito:
        flash(mensaje, "success")
    else:
        flash(mensaje, "warning")
        
    return redirect(url_for('finanzas.cuentas_por_cobrar'))

@finanzas_bp.route('/cxp', methods=['GET'])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def cuentas_por_pagar():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()
    estado = request.args.get('estado', 'pendientes').strip()
    
    ordenes_credito, ordenes_drop = obtener_cxp(request.args)
    tasas = obtener_tasas_cambio()
    
    lista_cxp = []
    total_por_pagar_usd = 0.0
    hoy = datetime.utcnow() - timedelta(hours=4)

    for o in ordenes_credito:
        total_compra_usd = float(o.total or 0.0)
        monto_abonado_usd = float(o.monto_abonado or 0.0)
        saldo_pendiente_usd = max(0.0, total_compra_usd - monto_abonado_usd)
        
        if estado in ['pendientes', 'parciales'] and saldo_pendiente_usd <= 0.01:
            continue
        if estado == 'pagadas' and saldo_pendiente_usd > 0.01:
            continue

        total_por_pagar_usd += saldo_pendiente_usd

        dias_vencido = 0
        if o.fecha_vencimiento and hoy > o.fecha_vencimiento:
            dias_vencido = (hoy - o.fecha_vencimiento).days

        lista_cxp.append({
            'id': o.id,
            'referencia': o.referencia,
            'fecha': o.fecha_creacion - timedelta(hours=4) if o.fecha_creacion else None,
            'proveedor_nombre': o.proveedor.nombre if o.proveedor else 'Proveedor General',
            'proveedor_telefono': o.proveedor.telefono if o.proveedor else '',
            'total_compra_usd': total_compra_usd,
            'monto_abonado_usd': monto_abonado_usd,
            'saldo_pendiente_usd': saldo_pendiente_usd,
            'porcentaje_pagado': min(100.0, round((monto_abonado_usd / total_compra_usd) * 100, 1)) if total_compra_usd > 0 else 0,
            'fecha_vencimiento': o.fecha_vencimiento - timedelta(hours=4) if o.fecha_vencimiento else None,
            'dias_vencido': dias_vencido,
            'estado_pago': o.estado_pago,
            'tipo_orden': 'compra',
            'pagos': o.pagos
        })
        
    for o in ordenes_drop:
        total_compra_usd = float(o.costo_total or 0.0)
        monto_abonado_usd = float(o.pago_proveedor_monto or 0.0)
        saldo_pendiente_usd = max(0.0, total_compra_usd - monto_abonado_usd)
        
        if estado in ['pendientes', 'parciales'] and saldo_pendiente_usd <= 0.01:
            continue
        if estado == 'pagadas' and saldo_pendiente_usd > 0.01:
            continue

        total_por_pagar_usd += saldo_pendiente_usd

        lista_cxp.append({
            'id': o.id,
            'referencia': o.referencia,
            'fecha': o.fecha_creacion - timedelta(hours=4) if o.fecha_creacion else None,
            'proveedor_nombre': o.proveedor.nombre if o.proveedor else 'Proveedor Dropshipping',
            'proveedor_telefono': o.proveedor.telefono if o.proveedor else '',
            'total_compra_usd': total_compra_usd,
            'monto_abonado_usd': monto_abonado_usd,
            'saldo_pendiente_usd': saldo_pendiente_usd,
            'porcentaje_pagado': min(100.0, round((monto_abonado_usd / total_compra_usd) * 100, 1)) if total_compra_usd > 0 else 0,
            'fecha_vencimiento': None,
            'dias_vencido': 0,
            'estado_pago': o.pago_proveedor_estado,
            'tipo_orden': 'dropshipping',
            'pagos': o.pagos_proveedor
        })
        
    lista_cxp.sort(key=lambda x: x['fecha'], reverse=True)
    
    total_items = len(lista_cxp)
    per_page = 20
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginacion = CustomPagination(page, per_page, total_items, lista_cxp[start_idx:end_idx])

    return render_template(
        'finanzas/cxp.html',
        paginacion=paginacion,
        lista_cxp=paginacion.items,
        total_por_pagar_usd=total_por_pagar_usd,
        tasa_bcv=tasas['bcv'],
        tasa_euro=tasas['euro'],
        tasa_usdt=tasas['usdt'],
        q=q,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        estado=estado
    )

@finanzas_bp.route('/cxp/abono/<int:orden_id>', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def registrar_abono_cxp(orden_id):
    asegurar_columnas_pagos()
    from models import OrdenCompra, OrdenDropshipping
    tipo_orden = request.form.get('tipo_orden', '').strip()
    
    # Si es dropshipping o no existe como compra pero sí como dropshipping:
    if tipo_orden == 'dropshipping' or not OrdenCompra.query.get(orden_id):
        orden_drop = OrdenDropshipping.query.get(orden_id)
        if orden_drop:
            return cxp_abonar_drop(orden_id)

    monto = sanitizar_decimal(request.form.get('monto'), default=0.0)
    metodo = request.form.get('metodo', 'Transferencia USD')
    referencia_pago = request.form.get('referencia_pago', '')
    tasa_raw = request.form.get('tasa_usada')
    moneda_tasa = request.form.get('moneda_tasa')
    monto_moneda_raw = request.form.get('monto_moneda')
    
    if monto <= 0:
        flash("El monto del abono debe ser mayor a 0.", "danger")
        return redirect(url_for('finanzas.cuentas_por_pagar'))

    tasa_usada = sanitizar_decimal(tasa_raw, default=None)
    monto_moneda = sanitizar_decimal(monto_moneda_raw, default=None)

    if tasa_usada and tasa_usada > 0:
        tasa_usada = round(tasa_usada, 4)
        if not monto_moneda or monto_moneda <= 0:
            monto_moneda = round(monto * tasa_usada, 2)
        else:
            monto_moneda = round(monto_moneda, 2)

        if not moneda_tasa or moneda_tasa in ['BCV', 'Tasa']:
            if 'USDT' in metodo or 'Binance' in metodo:
                moneda_tasa = 'USDT'
            elif 'EUR' in metodo or 'Euro' in metodo:
                moneda_tasa = 'EUR'
            else:
                moneda_tasa = 'BCV'
    else:
        tasa_usada = None
        monto_moneda = None
        
    exito, mensaje = srv_registrar_abono_cxp(orden_id, monto, metodo, referencia_pago, tasa_usada, moneda_tasa, monto_moneda)
    
    if exito and tasa_usada:
        from models import PagosCxP
        ultimo_pago = PagosCxP.query.filter_by(orden_id=orden_id).order_by(PagosCxP.id.desc()).first()
        if ultimo_pago:
            ultimo_pago.moneda_tasa = moneda_tasa
            ultimo_pago.monto_moneda = monto_moneda
            db.session.commit()

    if exito:
        flash(mensaje, "success")
    else:
        flash(mensaje, "warning")
        
    return redirect(url_for('finanzas.cuentas_por_pagar'))

@finanzas_bp.route('/cxp_abonar_drop/<int:orden_id>', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def cxp_abonar_drop(orden_id):
    asegurar_columnas_pagos()
    from models import OrdenCompra, OrdenDropshipping
    tipo_orden = request.form.get('tipo_orden', '').strip()
    
    # Si es compra tradicional o no existe como dropshipping pero sí como compra:
    if tipo_orden == 'compra' or not OrdenDropshipping.query.get(orden_id):
        orden_compra = OrdenCompra.query.get(orden_id)
        if orden_compra:
            return registrar_abono_cxp(orden_id)

    monto = sanitizar_decimal(request.form.get('monto'), default=0.0)
    metodo = request.form.get('metodo', 'Transferencia USD')
    referencia_pago = request.form.get('referencia_pago', '')
    tasa_raw = request.form.get('tasa_usada')
    moneda_tasa = request.form.get('moneda_tasa')
    monto_moneda_raw = request.form.get('monto_moneda')
    
    if monto <= 0:
        flash("El monto del abono debe ser mayor a 0.", "danger")
        return redirect(url_for('finanzas.cuentas_por_pagar'))

    tasa_usada = sanitizar_decimal(tasa_raw, default=None)
    monto_moneda = sanitizar_decimal(monto_moneda_raw, default=None)

    if tasa_usada and tasa_usada > 0:
        tasa_usada = round(tasa_usada, 4)
        if not monto_moneda or monto_moneda <= 0:
            monto_moneda = round(monto * tasa_usada, 2)
        else:
            monto_moneda = round(monto_moneda, 2)

        if not moneda_tasa or moneda_tasa in ['BCV', 'Tasa']:
            if 'USDT' in metodo or 'Binance' in metodo:
                moneda_tasa = 'USDT'
            elif 'EUR' in metodo or 'Euro' in metodo:
                moneda_tasa = 'EUR'
            else:
                moneda_tasa = 'BCV'
    else:
        tasa_usada = None
        monto_moneda = None
        
    exito, mensaje = srv_cxp_abonar_drop(orden_id, monto, metodo, referencia_pago, tasa_usada, moneda_tasa)
    
    if exito and tasa_usada:
        from models import PagosDropshipping
        ultimo_pago = PagosDropshipping.query.filter_by(orden_id=orden_id).order_by(PagosDropshipping.id.desc()).first()
        if ultimo_pago:
            ultimo_pago.moneda_tasa = moneda_tasa
            ultimo_pago.monto_moneda = monto_moneda
            db.session.commit()

    if exito:
        flash(mensaje, "success")
    else:
        flash(mensaje, "warning")
        
    return redirect(url_for('finanzas.cuentas_por_pagar'))

@finanzas_bp.route('/pagos', methods=['GET'])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def historial_pagos():
    page = request.args.get('page', 1, type=int)
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()
    metodo_pago = request.args.get('metodo_pago', '').strip()
    pagos, tipo_pago = obtener_historial_pagos(request.args, page)
    return render_template('finanzas/pagos.html', pagos=pagos, tipo_pago=tipo_pago, q=request.args.get('q', ''), fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, metodo_pago=metodo_pago)
