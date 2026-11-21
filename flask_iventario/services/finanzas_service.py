from models import GuiaDespacho, OrdenCompra, OrdenDropshipping, PagosCxC, PagosCxP, TasaCambio, Contactos
from extensions import db
from datetime import datetime
from sqlalchemy import func

def obtener_tasas_cambio():
    tasa_bcv_obj = TasaCambio.query.filter_by(fuente='BCV').order_by(TasaCambio.id.desc()).first()
    tasa_euro_obj = TasaCambio.query.filter_by(fuente='BCV_EURO').order_by(TasaCambio.id.desc()).first()
    tasa_usdt_obj = TasaCambio.query.filter_by(fuente='BINANCE_USDT').order_by(TasaCambio.id.desc()).first()
    
    return {
        'bcv': float(tasa_bcv_obj.tasa) if tasa_bcv_obj else 0.0,
        'euro': float(tasa_euro_obj.tasa) if tasa_euro_obj else 0.0,
        'usdt': float(tasa_usdt_obj.tasa) if tasa_usdt_obj else 0.0
    }

def obtener_cxc(filtros):
    q = filtros.get('q', '').strip()
    fecha_inicio = filtros.get('fecha_inicio', '').strip()
    fecha_fin = filtros.get('fecha_fin', '').strip()
    estado = filtros.get('estado', 'pendientes').strip()
    
    query = GuiaDespacho.query
    
    if estado == 'pendientes':
        query = query.filter(GuiaDespacho.estado_pago.in_(['Crédito', 'Parcial']))
    elif estado == 'pagadas':
        query = query.filter(GuiaDespacho.estado_pago == 'Pagada')
    elif estado == 'parciales':
        query = query.filter(GuiaDespacho.estado_pago == 'Parcial')
        
    if q:
        query = query.filter(db.or_(
            GuiaDespacho.referencia.ilike(f'%{q}%'),
            GuiaDespacho.cliente_nombre.ilike(f'%{q}%'),
            GuiaDespacho.cliente_identificacion.ilike(f'%{q}%')
        ))
        
    if fecha_inicio:
        try:
            dt_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            query = query.filter(func.date(GuiaDespacho.fecha) >= dt_inicio.date())
        except ValueError:
            pass

    if fecha_fin:
        try:
            dt_fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
            query = query.filter(func.date(GuiaDespacho.fecha) <= dt_fin.date())
        except ValueError:
            pass
            
    return query.order_by(GuiaDespacho.fecha.desc()).all()


def registrar_abono_cxc(guia_id, monto, metodo, referencia_pago, tasa_usada=None, moneda_tasa=None, monto_moneda=None):
    guia = GuiaDespacho.query.get_or_404(guia_id)
    
    total_venta_usd = round(float(guia.total or 0.0), 2)
    saldo_actual = max(0.0, total_venta_usd - float(guia.monto_abonado or 0.0))

    if monto > saldo_actual + 0.01:
        return False, f"El abono (${monto:.2f}) supera el saldo pendiente (${saldo_actual:.2f})."

    nuevo_abono = PagosCxC(
        guia_id=guia.id,
        fecha=datetime.utcnow(),
        monto=monto,
        metodo=metodo,
        referencia_pago=referencia_pago,
        tasa_usada=tasa_usada if tasa_usada else None,
        monto_moneda=monto_moneda if monto_moneda else None
    )
    db.session.add(nuevo_abono)

    guia.monto_abonado = float(guia.monto_abonado or 0.0) + monto
    if guia.monto_abonado >= total_venta_usd - 0.01:
        guia.estado_pago = 'Pagada'
    else:
        guia.estado_pago = 'Parcial'
    if guia.referencia and '-' in guia.referencia:
        base_ref = guia.referencia.split('-')[1]
        from models import OrdenDropshipping
        drops = OrdenDropshipping.query.filter(OrdenDropshipping.referencia.like(f'DROP-{base_ref}-%')).all()
        for d in drops:
            if guia.estado_pago == 'Pagada':
                d.pago_cliente_estado = 'Pagado'
                d.pago_cliente_monto = d.venta_total
            else:
                d.pago_cliente_estado = 'Parcial'

    db.session.commit()
    return True, f"¡Abono de ${monto:.2f} registrado con éxito!"

def obtener_cxp(filtros):
    q = filtros.get('q', '').strip()
    fecha_inicio = filtros.get('fecha_inicio', '').strip()
    fecha_fin = filtros.get('fecha_fin', '').strip()
    estado = filtros.get('estado', 'pendientes').strip()
    
    query_compra = OrdenCompra.query.outerjoin(Contactos, OrdenCompra.proveedor_id == Contactos.id)
    query_drop = OrdenDropshipping.query.outerjoin(Contactos, OrdenDropshipping.proveedor_id == Contactos.id)
    
    if estado == 'pendientes':
        query_compra = query_compra.filter(OrdenCompra.estado_pago.in_(['Crédito', 'Parcial']))
        query_drop = query_drop.filter(OrdenDropshipping.pago_proveedor_estado.in_(['Pendiente', 'Parcial']))
    elif estado == 'pagadas':
        query_compra = query_compra.filter(OrdenCompra.estado_pago == 'Pagada')
        query_drop = query_drop.filter(OrdenDropshipping.pago_proveedor_estado == 'Pagado')
    elif estado == 'parciales':
        query_compra = query_compra.filter(OrdenCompra.estado_pago == 'Parcial')
        query_drop = query_drop.filter(OrdenDropshipping.pago_proveedor_estado == 'Parcial')
    
    if q:
        query_compra = query_compra.filter(db.or_(
            OrdenCompra.referencia.ilike(f'%{q}%'),
            Contactos.nombre.ilike(f'%{q}%')
        ))
        query_drop = query_drop.filter(db.or_(
            OrdenDropshipping.referencia.ilike(f'%{q}%'),
            Contactos.nombre.ilike(f'%{q}%')
        ))
        
    if fecha_inicio:
        try:
            dt_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            query_compra = query_compra.filter(func.date(OrdenCompra.fecha_creacion) >= dt_inicio.date())
            query_drop = query_drop.filter(func.date(OrdenDropshipping.fecha_creacion) >= dt_inicio.date())
        except ValueError:
            pass

    if fecha_fin:
        try:
            dt_fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
            query_compra = query_compra.filter(func.date(OrdenCompra.fecha_creacion) <= dt_fin.date())
            query_drop = query_drop.filter(func.date(OrdenDropshipping.fecha_creacion) <= dt_fin.date())
        except ValueError:
            pass
            
    ordenes_credito = query_compra.order_by(OrdenCompra.fecha_creacion.desc()).all()
    ordenes_drop = query_drop.order_by(OrdenDropshipping.fecha_creacion.desc()).all()
    
    return ordenes_credito, ordenes_drop

def registrar_abono_cxp(orden_id, monto, metodo, referencia_pago, tasa_usada=None, moneda_tasa=None, monto_moneda=None):
    orden = OrdenCompra.query.get_or_404(orden_id)
    
    total_compra_usd = float(orden.total or 0.0)
    saldo_actual = max(0.0, total_compra_usd - float(orden.monto_abonado or 0.0))

    if monto > saldo_actual + 0.01:
        return False, f"El abono (${monto:.2f}) supera el saldo pendiente (${saldo_actual:.2f})."

    nuevo_abono = PagosCxP(
        orden_id=orden.id,
        fecha=datetime.utcnow(),
        monto=monto,
        metodo=metodo,
        referencia_pago=referencia_pago,
        tasa_usada=tasa_usada if tasa_usada else None,
        monto_moneda=monto_moneda if monto_moneda else None
    )
    db.session.add(nuevo_abono)

    orden.monto_abonado = float(orden.monto_abonado or 0.0) + monto
    if orden.monto_abonado >= total_compra_usd - 0.01:
        orden.estado_pago = 'Pagada'
    else:
        orden.estado_pago = 'Parcial'

    db.session.commit()
    return True, f"¡Abono a proveedor de ${monto:.2f} registrado con éxito!"

def cxp_abonar_drop(orden_id, monto, metodo="N/A", referencia_pago="", tasa_usada=None, moneda_tasa=None):
    from models import PagosDropshipping
    orden = OrdenDropshipping.query.get_or_404(orden_id)
    
    total_deuda = float(orden.costo_total or 0.0)
    saldo_actual = max(0.0, total_deuda - float(orden.pago_proveedor_monto or 0.0))

    if monto > saldo_actual + 0.01:
        return False, f"El abono (${monto:.2f}) supera el saldo pendiente (${saldo_actual:.2f})."

    orden.pago_proveedor_monto = float(orden.pago_proveedor_monto or 0.0) + monto
    if orden.pago_proveedor_monto >= total_deuda - 0.01:
        orden.pago_proveedor_estado = 'Pagado'
    else:
        orden.pago_proveedor_estado = 'Parcial'

    nuevo_pago = PagosDropshipping(
        orden_id=orden.id,
        monto=monto,
        metodo=metodo,
        referencia_pago=referencia_pago,
        tasa_usada=float(tasa_usada) if tasa_usada else None,
        moneda_tasa=moneda_tasa if moneda_tasa else None
    )
    db.session.add(nuevo_pago)
    db.session.commit()
    return True, f"¡Abono de ${monto:.2f} a Proveedor de Dropshipping registrado con éxito!"

def obtener_historial_pagos(filtros, page):
    from models import PagosCxC, PagosCxP, GuiaDespacho, OrdenCompra
    from sqlalchemy import desc, func
    from datetime import datetime
    
    tipo = filtros.get('tipo', 'recibidos')
    fecha_inicio = filtros.get('fecha_inicio', '').strip()
    fecha_fin = filtros.get('fecha_fin', '').strip()
    metodo_pago = filtros.get('metodo_pago', '').strip()
    
    if tipo == 'emitidos':
        query = PagosCxP.query.join(OrdenCompra).order_by(desc(PagosCxP.fecha))
        if filtros.get('q'):
            q = filtros.get('q')
            query = query.filter(
                OrdenCompra.referencia.ilike(f'%{q}%') | 
                OrdenCompra.proveedor_nombre.ilike(f'%{q}%') |
                PagosCxP.referencia_pago.ilike(f'%{q}%')
            )
        if fecha_inicio:
            try:
                dt_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                query = query.filter(func.date(PagosCxP.fecha) >= dt_inicio.date())
            except ValueError:
                pass
        if fecha_fin:
            try:
                dt_fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
                query = query.filter(func.date(PagosCxP.fecha) <= dt_fin.date())
            except ValueError:
                pass
        if metodo_pago:
            query = query.filter(PagosCxP.metodo.ilike(f'%{metodo_pago}%'))
            
        paginados = query.paginate(page=page, per_page=20, error_out=False)
        return paginados, 'emitidos'
    else:
        query = PagosCxC.query.join(GuiaDespacho).order_by(desc(PagosCxC.fecha))
        if filtros.get('q'):
            q = filtros.get('q')
            query = query.filter(
                GuiaDespacho.referencia.ilike(f'%{q}%') | 
                GuiaDespacho.cliente_nombre.ilike(f'%{q}%') |
                GuiaDespacho.cliente_identificacion.ilike(f'%{q}%') |
                PagosCxC.referencia_pago.ilike(f'%{q}%')
            )
        if fecha_inicio:
            try:
                dt_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                query = query.filter(func.date(PagosCxC.fecha) >= dt_inicio.date())
            except ValueError:
                pass
        if fecha_fin:
            try:
                dt_fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
                query = query.filter(func.date(PagosCxC.fecha) <= dt_fin.date())
            except ValueError:
                pass
        if metodo_pago:
            query = query.filter(PagosCxC.metodo.ilike(f'%{metodo_pago}%'))
            
        paginados = query.paginate(page=page, per_page=20, error_out=False)
        return paginados, 'recibidos'
