from models import OrdenCompra, DetalleOrdenCompra, Productos, Transacciones, PagosCxP
from extensions import db
from datetime import datetime
import uuid

def obtener_ordenes(filtros, page):
    from sqlalchemy import func
    from models import Contactos
    
    query = OrdenCompra.query.outerjoin(Contactos, OrdenCompra.proveedor_id == Contactos.id)
    
    q = filtros.get('q', '').strip()
    estado = filtros.get('estado', 'todos').strip()
    fecha_inicio = filtros.get('fecha_inicio', '').strip()
    fecha_fin = filtros.get('fecha_fin', '').strip()
    
    if q:
        query = query.filter(db.or_(
            OrdenCompra.referencia.ilike(f'%{q}%'),
            Contactos.nombre.ilike(f'%{q}%')
        ))
        
    if estado != 'todos':
        query = query.filter(OrdenCompra.estado == estado)
        
    if fecha_inicio:
        try:
            dt_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            query = query.filter(func.date(OrdenCompra.fecha_creacion) >= dt_inicio.date())
        except ValueError:
            pass

    if fecha_fin:
        try:
            dt_fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
            query = query.filter(func.date(OrdenCompra.fecha_creacion) <= dt_fin.date())
        except ValueError:
            pass

    query = query.order_by(OrdenCompra.fecha_creacion.desc())
    return query.paginate(page=page, per_page=20, error_out=False)

def crear_orden(proveedor_id, observaciones, detalles, form_data=None):
    """
    detalles es una lista de diccionarios: [{'producto_id': 1, 'cantidad': 10, 'costo': 50.0}]
    """
    if not form_data:
        form_data = {}
        
    tipo_pago = form_data.get('tipo_pago', 'Contado')
    dias_plazo = int(form_data.get('dias_plazo', 0))
    abono_inicial = float(form_data.get('abono_inicial', 0.0))
    
    estado_pago = 'Crédito' if tipo_pago == 'Crédito' else 'Pagada'
    
    fecha_vencimiento = None
    if estado_pago == 'Crédito' and dias_plazo > 0:
        import datetime as dt
        fecha_vencimiento = datetime.utcnow() + dt.timedelta(days=dias_plazo)
        
    referencia = f"OC-{uuid.uuid4().hex[:6].upper()}"
    nueva_orden = OrdenCompra(
        referencia=referencia,
        proveedor_id=proveedor_id,
        observaciones=observaciones,
        estado='En Tránsito', # Asumimos que al crearla ya viene en camino
        estado_pago=estado_pago,
        fecha_vencimiento=fecha_vencimiento
    )
    
    total = 0
    for d in detalles:
        producto_id = int(d['producto_id'])
        cantidad = int(d['cantidad'])
        costo = float(d['costo'])
        subtotal = cantidad * costo
        
        detalle = DetalleOrdenCompra(
            producto_id=producto_id,
            cantidad_pedida=cantidad,
            costo_unitario=costo,
            subtotal=subtotal
        )
        nueva_orden.detalles.append(detalle)
        total += subtotal
        
    nueva_orden.total = total
    
    # Calcular monto abonado
    monto_abonado = abono_inicial if estado_pago == 'Crédito' else total
    nueva_orden.monto_abonado = monto_abonado
    
    db.session.add(nueva_orden)
    db.session.flush() # para obtener nueva_orden.id
    
    metodo = form_data.get('metodo', 'Transferencia Bancaria (Bs)' if estado_pago == 'Pagada' else 'Abono Inicial')
    referencia_pago = form_data.get('referencia_pago', '')
    tasa_usada = float(form_data.get('tasa_usada')) if form_data.get('tasa_usada') else None
    moneda_tasa = form_data.get('moneda_tasa', 'BCV')
    monto_moneda = float(form_data.get('monto_moneda')) if form_data.get('monto_moneda') else None

    if estado_pago == 'Crédito' and abono_inicial > 0:
        primer_abono = PagosCxP(
            orden_id=nueva_orden.id,
            fecha=datetime.utcnow(),
            monto=abono_inicial,
            metodo=metodo,
            referencia_pago=referencia_pago if referencia_pago else 'Abono Inicial',
            tasa_usada=tasa_usada,
            moneda_tasa=moneda_tasa,
            monto_moneda=monto_moneda
        )
        db.session.add(primer_abono)
    elif estado_pago == 'Pagada' and total > 0:
        pago_completo = PagosCxP(
            orden_id=nueva_orden.id,
            fecha=datetime.utcnow(),
            monto=total,
            metodo=metodo,
            referencia_pago=referencia_pago if referencia_pago else 'Contado',
            tasa_usada=tasa_usada,
            moneda_tasa=moneda_tasa,
            monto_moneda=monto_moneda
        )
        db.session.add(pago_completo)
        
    db.session.commit()
    return nueva_orden.referencia

def recibir_mercancia_parcial(orden_id, recepciones):
    """
    recepciones es un diccionario con el formato { producto_id_str: cantidad_a_recibir_ahora }
    """
    orden = OrdenCompra.query.get_or_404(orden_id)
    
    if orden.estado in ['Recibida', 'Cancelada']:
        raise ValueError("Esta orden ya está completamente recibida o cancelada.")
        
    todas_recibidas = True
    
    for detalle in orden.detalles:
        prod_id_str = str(detalle.producto_id)
        
        # Extraemos cuánto dice el usuario que acaba de llegar en el camión
        cant_recibir_ahora = int(recepciones.get(prod_id_str, 0))
        
        if cant_recibir_ahora > 0:
            falta_por_recibir = detalle.cantidad_pedida - detalle.cantidad_recibida
            if cant_recibir_ahora > falta_por_recibir:
                raise ValueError(f"Estás intentando recibir más mercancía de la que pediste para el producto {detalle.producto.nombre}.")
                
            # 1. Sumamos a la orden de compra
            detalle.cantidad_recibida += cant_recibir_ahora
            
            # 2. Sumamos al inventario físico real y actualizamos costo
            producto = detalle.producto
            producto.cantidad += cant_recibir_ahora
            producto.costo = detalle.costo_unitario
            
            # 3. Guardamos el historial (Auditoría)
            transaccion = Transacciones(
                producto_id=producto.id,
                cantidad=cant_recibir_ahora,
                fecha=datetime.now(),
                tipo="ENTRADA POR COMPRA",
                referencia=orden.referencia
            )
            db.session.add(transaccion)
            
        # Si aún falta mercancía por llegar de este producto, la orden queda como Parcial
        if detalle.cantidad_recibida < detalle.cantidad_pedida:
            todas_recibidas = False
            
    if todas_recibidas:
        orden.estado = 'Recibida'
        orden.fecha_recepcion = datetime.now()
    else:
        orden.estado = 'Parcial'
        
    db.session.commit()
    return orden.estado

def anular_orden(orden_id):
    orden = OrdenCompra.query.get_or_404(orden_id)
    
    if orden.estado == 'Cancelada':
        raise ValueError("La orden ya se encuentra cancelada.")
        
    # Revertir inventario si se había recibido mercancía
    for detalle in orden.detalles:
        if detalle.cantidad_recibida > 0:
            producto = detalle.producto
            # Restamos del stock actual la cantidad que se había recibido
            producto.cantidad -= detalle.cantidad_recibida
            
            # Registrar transacción de salida
            transaccion = Transacciones(
                producto_id=producto.id,
                cantidad=detalle.cantidad_recibida,
                fecha=datetime.now(),
                tipo="SALIDA POR ANULACION DE COMPRA",
                referencia=orden.referencia
            )
            db.session.add(transaccion)
            
            # Restablecer a 0 la cantidad recibida
            detalle.cantidad_recibida = 0
            
    orden.estado = 'Cancelada'
    db.session.commit()
    return True

