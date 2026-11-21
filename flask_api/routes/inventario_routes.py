from models import Inventario, Productos, TasaCambio
from flask import Blueprint, request, flash, redirect, url_for, render_template, jsonify
from forms import CargaMasivaForm
from services.inventario_service import procesar_carga_masiva
from services.bcv_service import actualizar_tasa_bcv
from models import Transacciones, GuiaDespacho
from datetime import datetime, timedelta
from sqlalchemy import func
from extensions import db
from flask_login import current_user
import time

# Creamos un "plano" (Blueprint) para agrupar todas las URLs de inventario
inventario_bp = Blueprint("inventario", __name__)

@inventario_bp.before_request
def requerir_login():
    if not current_user.is_authenticated:
        flash("Debes iniciar sesión para acceder a esta página.", "warning")
        return redirect(url_for('auth.login'))

@inventario_bp.route("/")
def dashboard():
    tasa_bcv = TasaCambio.query.order_by(TasaCambio.fecha.desc()).first()

    # --- KPIs Y MÉTRICAS ---
    from sqlalchemy import func
    from datetime import timedelta
    hoy = datetime.now().date()
    
    # 1. Ventas de Hoy ($ y Bs)
    ventas_hoy_usd = db.session.query(func.sum(GuiaDespacho.total)).filter(
        func.date(GuiaDespacho.fecha) == hoy,
        GuiaDespacho.estado == 'Completada'
    ).scalar() or 0.0
    ventas_hoy_bs = float(ventas_hoy_usd) * float(tasa_bcv.tasa) if tasa_bcv else 0.0
    
    # 2. Órdenes Totales Hoy
    ordenes_hoy = GuiaDespacho.query.filter(
        func.date(GuiaDespacho.fecha) == hoy,
        GuiaDespacho.estado == 'Completada'
    ).count()
    
    # 3. Productos con Bajo Stock (<= 5 y activos)
    bajo_stock_count = Productos.query.filter(Productos.cantidad <= 5, Productos.deleted_at == None).count()
    productos_bajo_stock = Productos.query.filter(Productos.cantidad <= 5, Productos.deleted_at == None).order_by(Productos.cantidad.asc()).all()

    # 4. Datos para gráfico (Últimos 7 días)
    ventas_semana = []
    fechas_semana = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        total_dia = db.session.query(func.sum(GuiaDespacho.total)).filter(
            func.date(GuiaDespacho.fecha) == dia,
            GuiaDespacho.estado == 'Completada'
        ).scalar() or 0.0
        ventas_semana.append(float(total_dia))
        fechas_semana.append(dia.strftime("%d/%m"))

    return render_template('dashboard_kpis.html', 
                           tasa_bcv=tasa_bcv, 
                           ventas_hoy_usd=ventas_hoy_usd,
                           ventas_hoy_bs=ventas_hoy_bs,
                           ordenes_hoy=ordenes_hoy,
                           bajo_stock_count=bajo_stock_count,
                           productos_bajo_stock=productos_bajo_stock,
                           ventas_semana=ventas_semana,
                           fechas_semana=fechas_semana)

@inventario_bp.route("/productos")
def productos():
    # Parámetros de búsqueda y paginación
    page = request.args.get('page', 1, type=int)
    query_str = request.args.get('q', '').strip()
    eliminados = request.args.get('eliminados', '0')
    
    if eliminados == '1' and current_user.rol.nombre == 'Administrador':
        # Consultamos TODOS los productos que HAN sido eliminados (Papelera)
        query = Productos.query.filter(Productos.deleted_at != None)
    else:
        # Consultamos TODOS los productos que no han sido eliminados
        query = Productos.query.filter_by(deleted_at=None)

    if query_str:
        # Buscamos en nombre o descripción
        query = query.filter(db.or_(
            Productos.nombre.ilike(f'%{query_str}%'),
            Productos.descripcion.ilike(f'%{query_str}%')
        ))
        
    # Paginación (Ordenado por existencia de mayor a menor)
    productos_paginados = query.order_by(Productos.cantidad.desc(), Productos.nombre).paginate(page=page, per_page=50, error_out=False)
    
    # Obtenemos la última tasa registrada
    tasa_bcv = TasaCambio.query.order_by(TasaCambio.fecha.desc()).first()

    # Le pasamos la lista y la tasa al HTML
    return render_template('dashboard.html', 
                           productos=productos_paginados, 
                           tasa_bcv=tasa_bcv, 
                           query_str=query_str,
                           eliminados=eliminados)

@inventario_bp.route("/actualizar-tasa")
def actualizar_tasa():
    exito, mensaje = actualizar_tasa_bcv()
    if exito:
        flash(mensaje, "success")
    else:
        flash(mensaje, "danger")
    return redirect(url_for("inventario.productos"))

@inventario_bp.route("/descargar-pdf")
def descargar_pdf():
    from flask import send_file
    from datetime import datetime
    import io
    from xhtml2pdf import pisa

    # 1. Traemos los datos de la base de datos
    lista_productos = Productos.query.filter_by(deleted_at=None).all()
    tasa_bcv = TasaCambio.query.order_by(TasaCambio.fecha.desc()).first()
    fecha_actual = datetime.now().strftime("%d/%m/%Y")

    # 2. Renderizamos la plantilla HTML secreta del PDF (en texto)
    html_renderizado = render_template('pdf_template.html', 
                                       productos=lista_productos, 
                                       tasa_bcv=tasa_bcv, 
                                       fecha=fecha_actual)

    # 3. Convertimos el HTML a PDF en memoria
    pdf_en_memoria = io.BytesIO()
    # xhtml2pdf espera un string pero con CreatePDF se puede pasar un objeto file-like o texto
    pisa_status = pisa.CreatePDF(html_renderizado, dest=pdf_en_memoria)
    
    if pisa_status.err:
        flash("Error al generar el PDF", "danger")
        return redirect(url_for("inventario.productos"))
        
    pdf_en_memoria.seek(0)

    # 4. Se lo enviamos al usuario como una descarga
    return send_file(
        pdf_en_memoria,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'Reporte_Inventario_{datetime.now().strftime("%Y%m%d")}.pdf'
    )

  
@inventario_bp.route("/importar", methods=["GET", "POST"])

def importar_excel():
  # Instanciamos el escudo de seguridad (formulario) que creaste
  form = CargaMasivaForm()

  # Si el usuario hace clic en enviar y el archivo es seguro (.csv o .xlsx)
  if form.validate_on_submit():
    archivo = form.archivo.data
    # Llamamos al cerebro (Servicio) que hicimos en Pandas
    exito, mensaje = procesar_carga_masiva(archivo)

    if exito:
      flash(mensaje, "success") #Mensaje verde
      return redirect(url_for("inventario.productos"))
    
    else:
      flash(mensaje, "danger") #Mensaje Rojo

  # Si el usuario solo entra a la URL (GET), mostramos texto temporal
  # En la fase 7 reemplazaremos esto por una página web real (HTML)

  # Si el usuario solo entra a la URL (GET), mostramos texto temporal
  # En la fase 7 reemplazaremos esto por una página web real (HTML)
  return render_template('importar.html', form=form)

# ==========================================
# RUTAS DE CRUD MANUAL (Crear, Editar, Borrar)
# ==========================================
from forms import ProductosForm
from models import Categorias, Atributos, ValoresAtributos
from extensions import db

def cargar_opciones_form(form):
    """Ayudante para cargar las opciones de Categorías desde la BD"""
    # Categorías
    form.categoria_id.choices = [(0, "Sin Categoría")] + [(c.id, c.nombre) for c in Categorias.query.filter_by(deleted_at=None).order_by('nombre').all()]

@inventario_bp.route("/productos/nuevo", methods=["GET", "POST"])
def nuevo_producto():
    form = ProductosForm()
    cargar_opciones_form(form)
    
    if form.validate_on_submit():
        nuevo_prod = Productos(
            nombre=form.nombre.data,
            cantidad=form.cantidad.data,
            precio=form.precio.data,
            descripcion=form.descripcion.data,
            categoria_id=form.categoria_id.data if form.categoria_id.data > 0 else None
        )
        
        # Guardar Atributos dinámicos
        valores_ids = request.form.getlist('valores[]')
        for v_id in valores_ids:
            if v_id:
                valor_obj = ValoresAtributos.query.get(v_id)
                if valor_obj:
                    nuevo_prod.valores.append(valor_obj)
                
        db.session.add(nuevo_prod)
        db.session.commit()
        flash("Producto creado exitosamente", "success")
        return redirect(url_for("inventario.productos"))
        
    todos_atributos = Atributos.query.filter_by(deleted_at=None).order_by('nombre').all()
    return render_template("producto_form.html", form=form, es_edicion=False, atributos=todos_atributos, producto_valores=[])

@inventario_bp.route("/productos/editar/<int:id>", methods=["GET", "POST"])
def editar_producto(id):
    producto = Productos.query.get_or_404(id)
    form = ProductosForm(obj=producto)
    
    # Manejar el combo "Sin Categoría"
    if request.method == "GET" and producto.categoria_id is None:
        form.categoria_id.data = 0
        
    cargar_opciones_form(form)

    if form.validate_on_submit():
        producto.nombre = form.nombre.data
        producto.cantidad = form.cantidad.data
        producto.precio = form.precio.data
        producto.descripcion = form.descripcion.data
        producto.categoria_id = form.categoria_id.data if form.categoria_id.data > 0 else None
        
        # Actualizar Atributos dinámicos
        # Limpiamos los actuales
        producto.valores = []
        # Añadimos los que vienen en el formulario
        valores_ids = request.form.getlist('valores[]')
        for v_id in valores_ids:
            if v_id:
                valor_obj = ValoresAtributos.query.get(v_id)
                if valor_obj:
                    producto.valores.append(valor_obj)
        
        db.session.commit()
        flash("Producto actualizado exitosamente", "success")
        return redirect(url_for("inventario.productos"))
        
    # Obtener valores actuales para mostrarlos en la UI (array de IDs de valores)
    valores_actuales_ids = [v.id for v in producto.valores]
    todos_atributos = Atributos.query.filter_by(deleted_at=None).order_by('nombre').all()
    
    return render_template("producto_form.html", form=form, es_edicion=True, producto=producto, atributos=todos_atributos, producto_valores=valores_actuales_ids)

@inventario_bp.route("/productos/eliminar/<int:id>", methods=["POST"])
def eliminar_producto(id):
    producto = Productos.query.filter_by(id=id, deleted_at=None).first_or_404()
    # Soft delete: En lugar de destruir, marcamos la fecha de eliminación
    producto.deleted_at = datetime.now()
    db.session.commit()
    flash("Producto enviado a la papelera correctamente", "success")
    return redirect(url_for("inventario.productos"))

@inventario_bp.route("/productos/restaurar/<int:id>", methods=["POST"])
def restaurar_producto(id):
    producto = Productos.query.filter(Productos.id == id, Productos.deleted_at != None).first_or_404()
    producto.deleted_at = None
    db.session.commit()
    flash("Producto restaurado correctamente", "success")
    return redirect(url_for("inventario.productos", eliminados='1'))

from flask import jsonify


# ==========================================
# RUTAS DE AUDITORIA (HISTORIAL)
# ==========================================
@inventario_bp.route("/transacciones", methods=["GET"])
def historial_transacciones():
    page = request.args.get('page', 1, type=int)
    
    # Parámetros de filtro
    q = request.args.get('q', '').strip()
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()
    tipo = request.args.get('tipo', '').strip()
    
    query = Transacciones.query.join(Productos)
    
    if q:
        query = query.filter(db.or_(
            Transacciones.referencia.ilike(f'%{q}%'),
            Productos.nombre.ilike(f'%{q}%')
        ))
        
    if fecha_inicio:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            query = query.filter(func.date(Transacciones.fecha) >= fecha_inicio_dt.date())
        except ValueError:
            pass
            
    if fecha_fin:
        try:
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            query = query.filter(func.date(Transacciones.fecha) <= fecha_fin_dt.date())
        except ValueError:
            pass
            
    if tipo:
        query = query.filter(Transacciones.tipo == tipo)
    
    # Obtenemos las transacciones paginadas por fecha (más recientes primero)
    transacciones_paginadas = query.order_by(Transacciones.id.desc()).paginate(page=page, per_page=50, error_out=False)
    
    return render_template("transacciones.html", transacciones=transacciones_paginadas, q=q, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, tipo=tipo)

@inventario_bp.route("/productos/accion-masiva", methods=["POST"])
def accion_masiva_productos():
    ids_str = request.form.get("ids_seleccionados", "")
    accion = request.form.get("accion", "")
    
    if accion in ["excel_all", "pdf_all"]:
        productos = Productos.query.filter_by(deleted_at=None).all()
    else:
        if not ids_str:
            flash("No se seleccionaron productos.", "warning")
            return redirect(url_for("inventario.productos"))
            
        lista_ids = [int(i) for i in ids_str.split(",")]
        productos = Productos.query.filter(Productos.id.in_(lista_ids)).all()
    
    if accion == "delete":
        for p in productos:
            p.deleted_at = datetime.now()
        db.session.commit()
        flash(f"{len(productos)} productos eliminados correctamente.", "success")
        return redirect(url_for("inventario.productos"))
        
    elif accion in ["excel", "excel_all"]:
        import pandas as pd
        import io
        from flask import send_file
        
        datos = []
        for p in productos:
            cat_nombre = p.categoria.nombre if p.categoria else "Sin Categoría"
            datos.append({
                "Código": p.descripcion.replace("CÓDIGO: ", ""),
                "Nombre": p.nombre,
                "Categoría": cat_nombre,
                "Cantidad": p.cantidad,
                "Precio ($)": p.precio
            })
            
        df = pd.DataFrame(datos)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Productos')
        output.seek(0)
        
        nombre_archivo = "productos_catalogo_completo.xlsx" if accion == "excel_all" else "productos_seleccionados.xlsx"
        return send_file(output, download_name=nombre_archivo, as_attachment=True)
        
    elif accion in ["pdf", "pdf_all"]:
        import io
        from flask import send_file
        from xhtml2pdf import pisa
        
        tasa_bcv = TasaCambio.query.order_by(TasaCambio.fecha.desc()).first()
        html = render_template('pdf_template.html', productos=productos, tasa_bcv=tasa_bcv, fecha=datetime.now().strftime("%d/%m/%Y"))
        
        pdf_io = io.BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_io)
        if pisa_status.err:
            flash("Error al generar PDF", "danger")
            return redirect(url_for("inventario.productos"))
            
        pdf_io.seek(0)
        nombre_archivo = "productos_catalogo_completo.pdf" if accion == "pdf_all" else "productos_seleccionados.pdf"
        return send_file(pdf_io, download_name=nombre_archivo, as_attachment=True, mimetype='application/pdf')
        
    elif accion == "barcodes":
        return render_template('barcodes.html', productos=productos)

    return redirect(url_for("inventario.productos"))

@inventario_bp.route("/transacciones/accion-masiva", methods=["POST"])
def accion_masiva_transacciones():
    ids_str = request.form.get("ids_seleccionados", "")
    accion = request.form.get("accion", "")
    
    if not ids_str:
        flash("No se seleccionaron transacciones.", "warning")
        return redirect(url_for("inventario.historial_transacciones"))
        
    lista_ids = [int(i) for i in ids_str.split(",")]
    transacciones = Transacciones.query.filter(Transacciones.id.in_(lista_ids)).all()
    
    if accion == "excel":
        import pandas as pd
        import io
        from flask import send_file
        
        datos = []
        for t in transacciones:
            datos.append({
                "ID Transacción": t.id,
                "Referencia": t.referencia,
                "Fecha": t.fecha.strftime('%Y-%m-%d %H:%M') if t.fecha else "N/A",
                "Tipo": t.tipo,
                "Producto": t.producto.nombre if t.producto else "N/A",
                "Cant. Movida": t.cantidad
            })
            
        df = pd.DataFrame(datos)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Transacciones')
        output.seek(0)
        
        return send_file(output, download_name="transacciones.xlsx", as_attachment=True)
        
    elif accion == "pdf":
        import io
        from flask import send_file
        from xhtml2pdf import pisa
        
        html = render_template('transacciones_pdf.html', transacciones=transacciones, fecha=datetime.now().strftime("%d/%m/%Y"))
        
        pdf_io = io.BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_io)
        if pisa_status.err:
            flash("Error al generar PDF", "danger")
            return redirect(url_for("inventario.historial_transacciones"))
            
        pdf_io.seek(0)
        return send_file(pdf_io, download_name="transacciones.pdf", as_attachment=True, mimetype='application/pdf')

    return redirect(url_for("inventario.historial_transacciones"))


