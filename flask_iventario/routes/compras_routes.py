from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required
from services.compras_service import obtener_ordenes, crear_orden, recibir_mercancia_parcial, anular_orden
from models import Contactos, Productos, OrdenCompra
from extensions import db
from utils.decorators import rol_requerido

compras_bp = Blueprint("compras", __name__, url_prefix="/compras")

@compras_bp.before_request
@login_required
def requerir_login():
    pass

@compras_bp.route("/api/productos", methods=["GET"])
@login_required
def api_productos_compras():
    # Obtener TODOS los productos (no filtramos cantidad > 0 porque para comprar podemos necesitar items en 0)
    productos = Productos.query.filter(Productos.deleted_at == None).all()
    
    # Obtener el último costo de compra usando SQLAlchemy core para agrupar o directamente del historial
    from models import DetalleOrdenCompra
    detalles = db.session.query(DetalleOrdenCompra.producto_id, DetalleOrdenCompra.costo_unitario).order_by(DetalleOrdenCompra.id.desc()).all()
    ultimos_costos = {}
    for d in detalles:
        if d.producto_id not in ultimos_costos:
            ultimos_costos[d.producto_id] = float(d.costo_unitario)
            
    lista_productos = []
    from models import Atributos
    attr_marca = Atributos.query.filter_by(nombre="Marca").first()
    attr_marca_id = attr_marca.id if attr_marca else None
    
    for p in productos:
        marca = "Generica"
        if attr_marca_id:
            marca_val = next((v for v in p.valores if v.atributo_id == attr_marca_id), None)
            if marca_val:
                marca = marca_val.valor
                
        lista_productos.append({
            "id": p.id,
            "codigo": p.descripcion.replace('CÓDIGO: ', '') if p.descripcion else "",
            "nombre": p.nombre,
            "marca": marca,
            "stock": p.cantidad,
            "costo": ultimos_costos.get(p.id, float(p.costo) if p.costo else 0.0),
            "es_dropshipping": bool(p.es_dropshipping)
        })
    return jsonify(lista_productos)

@compras_bp.route("/", methods=["GET"])
@rol_requerido('Administrador', 'Supervisor')
def index():
    from datetime import timedelta
    page = request.args.get('page', 1, type=int)
    
    q = request.args.get('q', '').strip()
    estado = request.args.get('estado', 'todos').strip()
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()
    
    ordenes = obtener_ordenes(request.args, page)
    for o in ordenes.items:
        if o.fecha_creacion:
            o.fecha_local = o.fecha_creacion - timedelta(hours=4)
        else:
            o.fecha_local = None
            
    return render_template("compras/index.html", 
                           ordenes=ordenes, 
                           q=q, 
                           estado=estado, 
                           fecha_inicio=fecha_inicio, 
                           fecha_fin=fecha_fin)

@compras_bp.route("/crear", methods=["GET", "POST"])
@rol_requerido('Administrador', 'Supervisor')
def nueva_orden():
    if request.method == "POST":
        try:
            proveedor_id = request.form.get("proveedor_id")
            proveedor_nombre = request.form.get("proveedor_nombre")
            proveedor_identificacion = request.form.get("proveedor_identificacion")
            observaciones = request.form.get("observaciones", "")
            
            if not proveedor_id and proveedor_nombre:
                contacto_existente = Contactos.query.filter_by(identificacion=proveedor_identificacion).first() if proveedor_identificacion else None
                if contacto_existente:
                    proveedor_id = contacto_existente.id
                else:
                    nuevo_contacto = Contactos(
                        nombre=proveedor_nombre,
                        identificacion=proveedor_identificacion or "N/A",
                        direccion=request.form.get("proveedor_direccion"),
                        telefono=request.form.get("proveedor_telefono")
                    )
                    db.session.add(nuevo_contacto)
                    db.session.flush()
                    proveedor_id = nuevo_contacto.id

            if not proveedor_id:
                flash("Error: Debes seleccionar o ingresar los datos del proveedor.", "danger")
                return redirect(url_for('compras.nueva_orden'))

            productos_ids = request.form.getlist("producto_id[]")
            cantidades = request.form.getlist("cantidad[]")
            costos = request.form.getlist("costo[]")
            
            detalles = []
            for i in range(len(productos_ids)):
                if productos_ids[i] and cantidades[i] and costos[i]:
                    detalles.append({
                        "producto_id": productos_ids[i],
                        "cantidad": cantidades[i],
                        "costo": costos[i]
                    })
                    
            if not detalles:
                flash("Debes agregar al menos un producto a la orden.", "danger")
                return redirect(url_for("compras.nueva_orden"))
                
            ref = crear_orden(proveedor_id, observaciones, detalles, request.form)
            flash(f"Orden {ref} creada y en tránsito exitosamente.", "success")
            return redirect(url_for("compras.ver_recibo", referencia=ref))
        except Exception as e:
            flash(str(e), "danger")
            
    contactos = Contactos.query.filter_by(deleted_at=None).all()
    productos = Productos.query.filter_by(deleted_at=None).all()
    from services.finanzas_service import obtener_tasas_cambio
    tasas = obtener_tasas_cambio()
    return render_template(
        "compras/crear.html",
        contactos=contactos,
        productos=productos,
        tasa_bcv=tasas['bcv'],
        tasa_euro=tasas['euro'],
        tasa_usdt=tasas['usdt']
    )

@compras_bp.route("/recibo/<referencia>", methods=["GET"])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def ver_recibo(referencia):
    orden = OrdenCompra.query.filter_by(referencia=referencia).first_or_404()
    return render_template("compras/recibo.html", orden=orden)

@compras_bp.route("/recibir/<int:orden_id>", methods=["GET", "POST"])
@rol_requerido('Administrador', 'Supervisor')
def recibir(orden_id):
    orden = OrdenCompra.query.get_or_404(orden_id)
    
    if request.method == "POST":
        # Formato esperado: recepcion_X = cantidad recibida (donde X es el ID del producto)
        recepciones = {}
        for key, value in request.form.items():
            if key.startswith("recepcion_"):
                prod_id = key.split("_")[1]
                if value.strip(): # Si enviaron algún número
                    recepciones[prod_id] = value
                    
        try:
            nuevo_estado = recibir_mercancia_parcial(orden.id, recepciones)
            if nuevo_estado == 'Recibida':
                flash("¡Toda la mercancía ha sido recibida! La orden está completa.", "success")
            else:
                flash("Mercancía recibida parcialmente. La orden sigue abierta.", "info")
            return redirect(url_for("compras.index"))
        except Exception as e:
            flash(str(e), "danger")
            
    return render_template("compras/recibir.html", orden=orden)

@compras_bp.route("/anular/<int:orden_id>", methods=["POST"])
@rol_requerido('Administrador')
def anular(orden_id):
    try:
        anular_orden(orden_id)
        flash("La orden ha sido anulada exitosamente y el inventario (de existir) ha sido revertido.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("compras.index"))

