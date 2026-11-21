from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from extensions import db
from models import Productos, Atributos, GuiaDespacho, Transacciones
from datetime import datetime
from sqlalchemy import func
from flask_login import login_required

from services.ventas_service import procesar_nueva_venta

ventas_bp = Blueprint("ventas", __name__)

@ventas_bp.route("/ventas", methods=["GET"])
@login_required
def punto_de_venta():
    return render_template("ventas.html")

@ventas_bp.route("/api/productos", methods=["GET"])
@login_required
def api_obtener_productos():
    productos = Productos.query.filter(Productos.cantidad > 0, Productos.deleted_at == None).all()

    lista_productos = []
    for p in productos:
        marca = "Generica"
        attr_marca = Atributos.query.filter_by(nombre="Marca").first()
        if attr_marca:
            marca_val = next((v for v in p.valores if v.atributo_id == attr_marca.id), None)
            if marca_val:
                marca = marca_val.valor
                
        lista_productos.append({
            "id": p.id,
            "codigo": p.descripcion.replace('CÓDIGO: ', '') if p.descripcion else "",
            "nombre": p.nombre,
            "marca": marca,
            "precio": float(p.precio),
            "stock": p.cantidad
        })
    return jsonify(lista_productos)

@ventas_bp.route("/ventas/registrar", methods=["POST"])
@login_required
def registrar_venta():
    data = request.get_json()
    carrito = data.get("carrito", [])
    cliente = data.get("cliente", {})
    
    try:
        codigo_recibo = procesar_nueva_venta(cliente, carrito)
        return jsonify({"success": True, "message": "¡Venta procesada con éxito!", "referencia": codigo_recibo})
    except ValueError as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Ocurrió un error en el servidor."}), 500

@ventas_bp.route("/ventas/recibo/<referencia>", methods=["GET"])
@login_required
def imprimir_recibo(referencia):
    ref_original = referencia.replace('DEV-', '')
    guia = GuiaDespacho.query.filter_by(referencia=ref_original).first_or_404()
    transacciones = Transacciones.query.filter_by(referencia=referencia).all()
    es_devolucion = referencia.startswith('DEV-')
    
    return render_template("recibo.html", guia=guia, transacciones=transacciones, es_devolucion=es_devolucion)

@ventas_bp.route("/ventas/historial", methods=["GET"])
@login_required
def historial_ventas():
    page = request.args.get('page', 1, type=int)
    
    q = request.args.get('q', '').strip()
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()
    estado = request.args.get('estado', '').strip()
    
    query = GuiaDespacho.query
    
    if q:
        query = query.filter(db.or_(
            GuiaDespacho.referencia.ilike(f'%{q}%'),
            GuiaDespacho.cliente_nombre.ilike(f'%{q}%'),
            GuiaDespacho.cliente_identificacion.ilike(f'%{q}%')
        ))
        
    if fecha_inicio:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            query = query.filter(func.date(GuiaDespacho.fecha) >= fecha_inicio_dt.date())
        except ValueError:
            pass
            
    if fecha_fin:
        try:
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            query = query.filter(func.date(GuiaDespacho.fecha) <= fecha_fin_dt.date())
        except ValueError:
            pass
            
    if estado:
        query = query.filter(GuiaDespacho.estado == estado)
        
    guias_paginadas = query.order_by(GuiaDespacho.id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template("historial_ventas.html", guias=guias_paginadas, q=q, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, estado=estado)

@ventas_bp.route("/ventas/anular/<referencia>", methods=["POST"])
@login_required
def anular_venta(referencia):
    guia = GuiaDespacho.query.filter_by(referencia=referencia).first_or_404()
    
    if guia.estado == 'Anulada':
        flash("La venta ya se encuentra anulada.", "warning")
        return redirect(url_for('ventas.historial_ventas'))
        
    guia.estado = 'Anulada'
    
    transacciones = Transacciones.query.filter_by(referencia=referencia).all()
    
    for t in transacciones:
        if t.producto:
            t.producto.cantidad += t.cantidad
            
        devolucion = Transacciones(
            producto_id=t.producto_id,
            tipo="Devolución/Anulación",
            cantidad=t.cantidad,
            referencia=f"DEV-{referencia}",
            fecha=datetime.now()
        )
        db.session.add(devolucion)
        
    db.session.commit()
    flash(f"Venta {referencia} anulada exitosamente y stock devuelto.", "success")
    return redirect(url_for('ventas.historial_ventas'))
