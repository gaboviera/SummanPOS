from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, OrdenDropshipping, DetalleDropshipping, Contactos, Productos, Notificacion, Transacciones, TasaCambio
from utils.decorators import rol_requerido
from datetime import datetime
import json

dropshipping_bp = Blueprint('dropshipping', __name__)

@dropshipping_bp.before_request
def verificar_modulo_activo():
    # Permitir consultas a recibos o PDFs historicos
    if request.endpoint and ('recibo' in request.endpoint or 'pdf' in request.endpoint):
        return None
    from models import Configuracion
    conf = Configuracion.query.filter_by(clave="modulo_dropshipping_activo").first()
    activo = (conf.valor.lower() in ['true', '1', 'si']) if conf else False
    if not activo:
        flash("El módulo de Dropshipping está actualmente desactivado en la configuración del sistema.", "warning")
        return redirect(url_for("inventario.index"))

@dropshipping_bp.route('/dropshipping')
@login_required
@rol_requerido('Administrador', 'Supervisor')
def index():
    from datetime import timedelta, datetime
    from sqlalchemy import func
    
    q = request.args.get('q', '').strip()
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()
    estado = request.args.get('estado', '').strip()
    
    query = OrdenDropshipping.query.join(Contactos, OrdenDropshipping.cliente_id == Contactos.id)
    
    if q:
        query = query.filter(db.or_(
            OrdenDropshipping.referencia.ilike(f'%{q}%'),
            Contactos.nombre.ilike(f'%{q}%'),
            Contactos.identificacion.ilike(f'%{q}%')
        ))
        
    if fecha_inicio:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            query = query.filter(func.date(OrdenDropshipping.fecha_creacion) >= fecha_inicio_dt.date())
        except ValueError:
            pass
            
    if fecha_fin:
        try:
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            query = query.filter(func.date(OrdenDropshipping.fecha_creacion) <= fecha_fin_dt.date())
        except ValueError:
            pass
            
    if estado:
        query = query.filter(OrdenDropshipping.estado == estado)
        
    page = request.args.get('page', 1, type=int)
    paginacion = query.order_by(OrdenDropshipping.fecha_creacion.desc()).paginate(page=page, per_page=15, error_out=False)
    ordenes = paginacion.items
    
    for o in ordenes:
        if o.fecha_creacion:
            o.fecha_local = o.fecha_creacion - timedelta(hours=4)
        else:
            o.fecha_local = None
            
    return render_template('dropshipping/index.html', ordenes=ordenes, paginacion=paginacion)

@dropshipping_bp.route('/dropshipping/crear', methods=['GET', 'POST'])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def crear():
    if request.method == 'POST':
        try:
            data = request.json
            
            # Generar referencia única
            ultima_orden = OrdenDropshipping.query.order_by(OrdenDropshipping.id.desc()).first()
            siguiente_id = (ultima_orden.id + 1) if ultima_orden else 1
            referencia = f"DROP-{str(siguiente_id).zfill(5)}"
            
            nueva_orden = OrdenDropshipping(
                referencia=referencia,
                cliente_id=data['cliente_id'],
                proveedor_id=data['proveedor_id'],
                estado='Pendiente',
            vendedor_id=current_user.id
            )
            
            total_costo = 0
            total_venta = 0
            
            for item in data['productos']:
                cantidad = int(item['cantidad'])
                costo_unitario = float(item['costo'])
                precio_venta = float(item['precio'])
                
                detalle = DetalleDropshipping(
                    producto_id=item['producto_id'],
                    cantidad=cantidad,
                    costo_unitario=costo_unitario,
                    precio_venta_unitario=precio_venta
                )
                nueva_orden.detalles.append(detalle)
                
                total_costo += (costo_unitario * cantidad)
                total_venta += (precio_venta * cantidad)
            
            nueva_orden.costo_total = total_costo
            nueva_orden.venta_total = total_venta
            nueva_orden.ganancia = total_venta - total_costo
            
            db.session.add(nueva_orden)
            
            # Generar transacciones de venta dropshipping
            for item in data['productos']:
                producto = Productos.query.get(item['producto_id'])
                if producto:
                    transaccion = Transacciones(
                        producto_id=producto.id,
                        cantidad=int(item['cantidad']),
                        fecha=datetime.now(),
                        tipo='Venta Dropshipping',
                        stock_anterior=producto.cantidad,
                        referencia=referencia
                    )
                    db.session.add(transaccion)
            
            # Crear notificación
            noti = Notificacion(
                mensaje=f"Nueva Orden Dropshipping {referencia} creada. Ganancia esperada: ${nueva_orden.ganancia:.2f}",
                tipo='success'
            )
            db.session.add(noti)
            
            db.session.commit()
            
            return jsonify({'success': True, 'url': url_for('dropshipping.index')})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    clientes = Contactos.query.filter_by(deleted_at=None).order_by(Contactos.nombre).all()
    proveedores = Contactos.query.filter_by(deleted_at=None).order_by(Contactos.nombre).all()
    productos = Productos.query.filter_by(deleted_at=None).order_by(Productos.nombre).all()
    
    return render_template('dropshipping/crear.html', clientes=clientes, proveedores=proveedores, productos=productos)

@dropshipping_bp.route('/dropshipping/<int:id>', methods=['GET'])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def detalle(id):
    orden = OrdenDropshipping.query.get_or_404(id)
    tasa_bcv_obj = TasaCambio.query.filter_by(fuente='BCV').order_by(TasaCambio.id.desc()).first()
    tasa_euro_obj = TasaCambio.query.filter_by(fuente='BCV_EURO').order_by(TasaCambio.id.desc()).first()
    tasa_usdt_obj = TasaCambio.query.filter_by(fuente='BINANCE_USDT').order_by(TasaCambio.id.desc()).first()
    
    tasa_bcv = float(tasa_bcv_obj.tasa) if tasa_bcv_obj else 0.0
    tasa_euro = float(tasa_euro_obj.tasa) if tasa_euro_obj else 0.0
    tasa_usdt = float(tasa_usdt_obj.tasa) if tasa_usdt_obj else 0.0

    return render_template(
        'dropshipping/detalle.html',
        orden=orden,
        tasa_bcv=tasa_bcv,
        tasa_euro=tasa_euro,
        tasa_usdt=tasa_usdt
    )

@dropshipping_bp.route('/dropshipping/<int:id>/tracking', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def actualizar_tracking(id):
    orden = OrdenDropshipping.query.get_or_404(id)
    
    nuevo_estado = request.form.get('estado')
    empresa = request.form.get('empresa_transporte')
    tracking = request.form.get('numero_seguimiento')
    
    pago_cliente = request.form.get('pago_cliente_estado')
    pago_proveedor = request.form.get('pago_proveedor_estado')
    
    pago_cliente_monto = request.form.get('pago_cliente_monto')
    pago_proveedor_monto = request.form.get('pago_proveedor_monto')
    
    if nuevo_estado:
        orden.estado = nuevo_estado
    if empresa:
        orden.empresa_transporte = empresa
    if tracking:
        orden.numero_seguimiento = tracking
    
    if pago_cliente:
        orden.pago_cliente_estado = pago_cliente
        if pago_cliente == 'Parcial' and pago_cliente_monto:
            try:
                monto = float(pago_cliente_monto)
                if monto > float(orden.venta_total):
                    flash(f"Error: El abono al cliente (${monto}) no puede superar el total a cobrar (${orden.venta_total}).", "danger")
                    return redirect(url_for('dropshipping.detalle', id=orden.id))
                orden.pago_cliente_monto = monto
            except ValueError:
                pass
        else:
            orden.pago_cliente_monto = 0.00
            
    if pago_proveedor:
        orden.pago_proveedor_estado = pago_proveedor
        if pago_proveedor == 'Parcial' and pago_proveedor_monto:
            try:
                monto = float(pago_proveedor_monto)
                if monto > float(orden.costo_total):
                    flash(f"Error: El abono al proveedor (${monto}) no puede superar el total a pagar (${orden.costo_total}).", "danger")
                    return redirect(url_for('dropshipping.detalle', id=orden.id))
                orden.pago_proveedor_monto = monto
            except ValueError:
                pass
        else:
            orden.pago_proveedor_monto = 0.00
        
    db.session.commit()
    flash(f"Información de la orden {orden.referencia} actualizada.", "success")
    return redirect(url_for('dropshipping.detalle', id=orden.id))

@dropshipping_bp.route('/dropshipping/recibo/<int:id>')
@login_required
@rol_requerido('Administrador', 'Supervisor')
def recibo(id):
    orden = OrdenDropshipping.query.get_or_404(id)
    return render_template('dropshipping/recibo_pdf.html', orden=orden)

@dropshipping_bp.route('/dropshipping/reporte')
@login_required
@rol_requerido('Administrador', 'Supervisor')
def reporte():
    from datetime import datetime
    
    ordenes = OrdenDropshipping.query.order_by(OrdenDropshipping.fecha_creacion.desc()).all()
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    
    return render_template('dropshipping/reporte_pdf.html', ordenes=ordenes, fecha=fecha_actual)

@dropshipping_bp.route('/dropshipping/productos')
@login_required
@rol_requerido('Administrador', 'Supervisor')
def productos():
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    page = request.args.get('page', 1, type=int)
    query_str = request.args.get('q', '').strip()
    estado_envio = request.args.get('estado_envio', 'todos')
    estado_pago = request.args.get('estado_pago', 'todos')
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()

    query = db.session.query(DetalleDropshipping).join(OrdenDropshipping).join(Productos)

    if query_str:
        query = query.filter(db.or_(
            Productos.nombre.ilike(f'%{query_str}%'),
            Productos.descripcion.ilike(f'%{query_str}%'),
            OrdenDropshipping.referencia.ilike(f'%{query_str}%')
        ))

    if estado_envio != 'todos':
        query = query.filter(OrdenDropshipping.estado == estado_envio)
        
    if estado_pago != 'todos':
        query = query.filter(OrdenDropshipping.pago_cliente_estado == estado_pago)
        
    if fecha_inicio:
        try:
            # Como la DB está en UTC, añadimos un pequeño ajuste si es necesario o comparamos directo
            dt_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            query = query.filter(func.date(OrdenDropshipping.fecha_creacion) >= dt_inicio.date())
        except ValueError:
            pass

    if fecha_fin:
        try:
            dt_fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
            query = query.filter(func.date(OrdenDropshipping.fecha_creacion) <= dt_fin.date())
        except ValueError:
            pass

    query = query.order_by(OrdenDropshipping.fecha_creacion.desc())
    detalles_paginados = query.paginate(page=page, per_page=50, error_out=False)

    for d in detalles_paginados.items:
        if d.orden.fecha_creacion:
            d.orden.fecha_local = d.orden.fecha_creacion - timedelta(hours=4)
        else:
            d.orden.fecha_local = None

    return render_template('dropshipping/productos.html', 
                           detalles=detalles_paginados, 
                           query_str=query_str, 
                           estado_envio=estado_envio,
                           estado_pago=estado_pago,
                           fecha_inicio=fecha_inicio,
                           fecha_fin=fecha_fin)

@dropshipping_bp.route('/dropshipping/productos/<int:id>/toggle', methods=['POST'])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def toggle_dropshipping(id):
    producto = Productos.query.get_or_404(id)
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado', False)
        producto.es_dropshipping = nuevo_estado
        db.session.commit()
        return jsonify({'success': True, 'es_dropshipping': producto.es_dropshipping})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@dropshipping_bp.route('/dropshipping/recibo_ref/<string:referencia>')
@login_required
@rol_requerido('Administrador', 'Supervisor')
def recibo_ref(referencia):
    orden = OrdenDropshipping.query.filter_by(referencia=referencia).first_or_404()
    return render_template('dropshipping/recibo_pdf.html', orden=orden)
