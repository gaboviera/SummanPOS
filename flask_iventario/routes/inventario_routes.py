from models import Inventario, Productos, TasaCambio
from flask import Blueprint, request, flash, redirect, url_for, render_template, jsonify, send_file
from forms import CargaMasivaForm
from services.inventario_service import procesar_carga_masiva, obtener_historial_filtrado
from services.bcv_service import actualizar_tasa_bcv
from models import Transacciones, GuiaDespacho
from datetime import datetime, timedelta
from sqlalchemy import func
from extensions import db
from flask_login import current_user
import time
from sqlalchemy.orm import joinedload
from utils.decorators import rol_requerido

# Creamos un "plano" (Blueprint) para agrupar todas las URLs de inventario
inventario_bp = Blueprint("inventario", __name__)

@inventario_bp.before_request
def requerir_login():
    if not current_user.is_authenticated:
        flash("Debes iniciar sesión para acceder a esta página.", "warning")
        return redirect(url_for('auth.login'))

@inventario_bp.route("/dashboard")
def dashboard():
    tasa_bcv = TasaCambio.query.filter_by(fuente='BCV').order_by(TasaCambio.id.desc()).first()
    tasa_euro = TasaCambio.query.filter_by(fuente='BCV_EURO').order_by(TasaCambio.id.desc()).first()
    tasa_usdt = TasaCambio.query.filter_by(fuente='BINANCE_USDT').order_by(TasaCambio.id.desc()).first()

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
                           tasa_euro=tasa_euro,
                           tasa_usdt=tasa_usdt,
                           ventas_hoy_usd=ventas_hoy_usd,
                           ventas_hoy_bs=ventas_hoy_bs,
                           ordenes_hoy=ordenes_hoy,
                           bajo_stock_count=bajo_stock_count,
                           productos_bajo_stock=productos_bajo_stock,
                           ventas_semana=ventas_semana,
                           fechas_semana=fechas_semana)

def calcular_precio_lista_regla(p, lista):
    """Calcula el precio en USD aplicando la regla de la lista de precios o precio alternativo asignado"""
    if not lista:
        return float(p.precio or 0.0)
    for alt in getattr(p, 'precios_alternativos', []):
        if alt.lista_id == lista.id:
            return float(alt.precio)
    base_calc = float(p.precio or 0.0) if lista.basado_en == 'precio_base' else float(p.costo or 0.0)
    valor_regla = float(lista.valor_regla or 0.0)
    if lista.tipo == 'Porcentaje':
        mod = base_calc * (valor_regla / 100.0)
        final_val = base_calc + mod if lista.operador == '+' else base_calc - mod
    elif lista.tipo == 'Monto Fijo':
        final_val = base_calc + valor_regla if lista.operador == '+' else base_calc - valor_regla
    else:
        final_val = base_calc
    return round(max(0.0, final_val), 2)

@inventario_bp.route("/productos/lista-precios")
@inventario_bp.route("/lista-precios")
def lista_precios():
    from models import Categorias, ListasPrecios
    
    # Parámetros de búsqueda y filtros
    page = request.args.get('page', 1, type=int)
    query_str = request.args.get('q', '').strip()
    categoria_id = request.args.get('categoria_id', type=int)
    estado_stock = request.args.get('estado_stock', '')
    es_dropshipping = request.args.get('es_dropshipping', '')

    tasa_bcv = TasaCambio.query.filter_by(fuente='BCV').order_by(TasaCambio.id.desc()).first()
    tasa_euro = TasaCambio.query.filter_by(fuente='BCV_EURO').order_by(TasaCambio.id.desc()).first()
    tasa_usdt = TasaCambio.query.filter_by(fuente='BINANCE_USDT').order_by(TasaCambio.id.desc()).first()

    # Listas de precios configuradas en /configuracion/listas-precios
    listas_activas = ListasPrecios.query.filter_by(activa=True).order_by(ListasPrecios.id.asc()).all()
    lista_bcv = next((l for l in listas_activas if l.moneda == 'BCV' or 'bcv' in l.nombre.lower()), None)
    lista_usdt = next((l for l in listas_activas if l.moneda == 'USDT' or 'usdt' in l.nombre.lower()), None)
    lista_mayorista = next((l for l in listas_activas if 'mayorista' in l.nombre.lower()), None)
    lista_euro = next((l for l in listas_activas if l.moneda == 'EURO' or 'euro' in l.nombre.lower()), None)

    query = Productos.query.filter_by(deleted_at=None)

    if query_str:
        query = query.filter(db.or_(
            Productos.nombre.ilike(f'%{query_str}%'),
            Productos.descripcion.ilike(f'%{query_str}%')
        ))

    if categoria_id:
        query = query.filter(Productos.categoria_id == categoria_id)

    if estado_stock == 'con_stock':
        query = query.filter(Productos.cantidad > 0)
    elif estado_stock == 'sin_stock':
        query = query.filter(Productos.cantidad == 0)

    if es_dropshipping == 'si':
        query = query.filter(Productos.es_dropshipping == True)
    elif es_dropshipping == 'no':
        query = query.filter((Productos.es_dropshipping == False) | (Productos.es_dropshipping == None))

    query = query.outerjoin(Categorias, Productos.categoria_id == Categorias.id).order_by(
        Categorias.nombre.asc(), Productos.nombre.asc()
    )

    productos_paginados = query.paginate(page=page, per_page=50, error_out=False)
    categorias = Categorias.query.filter_by(deleted_at=None).order_by(Categorias.nombre.asc()).all()

    total_productos = Productos.query.filter_by(deleted_at=None).count()
    total_con_stock = Productos.query.filter(Productos.deleted_at == None, Productos.cantidad > 0).count()

    # Precalcular precios basados exactamente en las reglas de /configuracion/listas-precios
    tasa_bcv_val = float(tasa_bcv.tasa) if tasa_bcv else 0.0
    tasa_usdt_val = float(tasa_usdt.tasa) if tasa_usdt else 0.0
    tasa_euro_val = float(tasa_euro.tasa) if tasa_euro else 0.0

    items_calculados = []
    for p in productos_paginados.items:
        precio_base = float(p.precio or 0.0)
        
        # 1. Precio BCV según regla de ListasPrecios (ej: +20%)
        precio_usd_bcv = calcular_precio_lista_regla(p, lista_bcv)
        precio_bs_bcv = precio_usd_bcv * tasa_bcv_val
        
        # 2. Precio USDT según regla de ListasPrecios (ej: +0%)
        precio_usd_usdt = calcular_precio_lista_regla(p, lista_usdt)
        precio_bs_usdt = precio_usd_usdt * tasa_usdt_val

        # 3. Precio Mayorista según regla de ListasPrecios (ej: -15%)
        precio_usd_mayorista = calcular_precio_lista_regla(p, lista_mayorista) if lista_mayorista else None

        # 4. Precio Euro
        precio_usd_euro = calcular_precio_lista_regla(p, lista_euro) if lista_euro else None
        precio_bs_euro = precio_usd_euro * tasa_euro_val if precio_usd_euro else 0.0

        codigo = p.descripcion.replace('CÓDIGO: ', '').replace('CODIGO: ', '') if p.descripcion else f'PROD-{p.id}'

        items_calculados.append({
            'producto': p,
            'codigo': codigo,
            'precio_base': precio_base,
            'precio_usd_bcv': precio_usd_bcv,
            'precio_bs_bcv': precio_bs_bcv,
            'precio_usd_usdt': precio_usd_usdt,
            'precio_bs_usdt': precio_bs_usdt,
            'precio_usd_mayorista': precio_usd_mayorista,
            'precio_usd_euro': precio_usd_euro,
            'precio_bs_euro': precio_bs_euro
        })

    return render_template('lista_precios_preview.html',
                           items_calculados=items_calculados,
                           productos=productos_paginados,
                           categorias=categorias,
                           listas_activas=listas_activas,
                           lista_bcv=lista_bcv,
                           lista_usdt=lista_usdt,
                           lista_mayorista=lista_mayorista,
                           lista_euro=lista_euro,
                           tasa_bcv=tasa_bcv,
                           tasa_euro=tasa_euro,
                           tasa_usdt=tasa_usdt,
                           q=query_str,
                           categoria_id=categoria_id,
                           estado_stock=estado_stock,
                           es_dropshipping=es_dropshipping,
                           total_productos=total_productos,
                           total_con_stock=total_con_stock)


@inventario_bp.route("/productos/lista-precios/exportar", methods=["POST"])
def exportar_lista_precios():
    import copy
    import io
    import pandas as pd
    from datetime import datetime
    from models import Categorias, ListasPrecios, TasaCambio
    from xhtml2pdf import pisa

    formato = request.form.get("formato", "excel")
    lista_opcion = request.form.get("lista_opcion", "bcv")
    mostrar_cantidad = request.form.get("mostrar_cantidad") == "si"
    alcance = request.form.get("alcance", "catalogo")
    
    q = request.form.get("q", "").strip()
    categoria_id = request.form.get("categoria_id", type=int)
    estado_stock = request.form.get("estado_stock", "")
    es_dropshipping = request.form.get("es_dropshipping", "")

    query = Productos.query.filter_by(deleted_at=None)

    ids_str = request.form.get("ids_seleccionados", "").strip()

    # Alcance de la exportación
    if alcance == "seleccionados":
        if not ids_str:
            flash("No se seleccionaron productos para exportar.", "warning")
            return redirect(url_for("inventario.lista_precios"))
        lista_ids = [int(i) for i in ids_str.split(",") if i.strip().isdigit()]
        query = query.filter(Productos.id.in_(lista_ids))
    elif alcance == "filtrados":
        if q:
            query = query.filter(db.or_(
                Productos.nombre.ilike(f'%{q}%'),
                Productos.descripcion.ilike(f'%{q}%')
            ))
        if categoria_id:
            query = query.filter(Productos.categoria_id == categoria_id)
        if estado_stock == 'con_stock':
            query = query.filter(Productos.cantidad > 0)
        elif estado_stock == 'sin_stock':
            query = query.filter(Productos.cantidad == 0)
        if es_dropshipping == 'si':
            query = query.filter(Productos.es_dropshipping == True)
        elif es_dropshipping == 'no':
            query = query.filter((Productos.es_dropshipping == False) | (Productos.es_dropshipping == None))

    query = query.outerjoin(Categorias, Productos.categoria_id == Categorias.id).options(
        joinedload(Productos.precios_alternativos)
    ).order_by(Categorias.nombre.asc(), Productos.nombre.asc())
    
    productos = query.all()
    if not productos:
        flash("No hay productos para exportar con los filtros seleccionados.", "warning")
        return redirect(url_for("inventario.lista_precios"))

    listas_activas = ListasPrecios.query.filter_by(activa=True).all()
    lista_bcv = next((l for l in listas_activas if l.moneda == 'BCV' or 'bcv' in l.nombre.lower()), None)
    lista_usdt = next((l for l in listas_activas if l.moneda == 'USDT' or 'usdt' in l.nombre.lower()), None)
    lista_mayorista = next((l for l in listas_activas if 'mayorista' in l.nombre.lower()), None)
    lista_euro = next((l for l in listas_activas if l.moneda == 'EURO' or 'euro' in l.nombre.lower()), None)

    # Determinar la lista seleccionada
    lista_seleccionada = None
    nombre_lista_archivo = "completo"
    nombre_columna_precio = "Precio ($)"
    
    if lista_opcion == "base":
        nombre_lista_archivo = "Efectivo_Base"
        nombre_columna_precio = "Precio ($)"
    elif lista_opcion == "bcv":
        lista_seleccionada = lista_bcv
        nombre_lista_archivo = "Precio_BCV"
        nombre_columna_precio = "Precio ($)"
    elif lista_opcion == "usdt":
        lista_seleccionada = lista_usdt
        nombre_lista_archivo = "Precio_USDT"
        nombre_columna_precio = "Precio ($)"
    elif lista_opcion == "mayorista":
        lista_seleccionada = lista_mayorista
        nombre_lista_archivo = "Mayorista"
        nombre_columna_precio = "Precio ($)"
    elif lista_opcion == "euro":
        lista_seleccionada = lista_euro
        nombre_lista_archivo = "Precio_Euro"
        nombre_columna_precio = "Precio Euro ($)"
    elif lista_opcion.isdigit():
        lista_seleccionada = ListasPrecios.query.get(int(lista_opcion))
        if lista_seleccionada:
            nombre_lista_archivo = lista_seleccionada.nombre.replace(" ", "_")

    if formato == "excel":
        datos = []
        last_cat_nombre = None

        for p in productos:
            cat_nombre = p.categoria.nombre if p.categoria else "SIN CATEGORÍA"
            cod = p.descripcion.replace("CÓDIGO: ", "").replace("CODIGO: ", "") if p.descripcion else f"PROD-{p.id}"

            if lista_opcion == "todas":
                # Fila de separación de categoría
                if cat_nombre != last_cat_nombre:
                    cat_row = {"Código": cat_nombre, "Nombre": None}
                    if mostrar_cantidad:
                        cat_row["Cantidad"] = None
                    cat_row["Efectivo ($)"] = None
                    cat_row["Precio BCV ($)"] = None
                    cat_row["Precio USDT ($)"] = None
                    cat_row["Precio Euro ($)"] = None
                    cat_row["Mayorista ($)"] = None
                    datos.append(cat_row)
                    last_cat_nombre = cat_nombre

                p_base = float(p.precio or 0.0)
                p_bcv = calcular_precio_lista_regla(p, lista_bcv)
                p_usdt = calcular_precio_lista_regla(p, lista_usdt)
                p_euro = calcular_precio_lista_regla(p, lista_euro) if lista_euro else None
                p_may = calcular_precio_lista_regla(p, lista_mayorista) if lista_mayorista else None

                fila = {
                    "Código": cod,
                    "Nombre": p.nombre
                }
                if mostrar_cantidad:
                    fila["Cantidad"] = p.cantidad
                fila["Efectivo ($)"] = p_base
                fila["Precio BCV ($)"] = p_bcv
                fila["Precio USDT ($)"] = p_usdt
                fila["Precio Euro ($)"] = p_euro
                fila["Mayorista ($)"] = p_may
                datos.append(fila)

            else:
                # Fila de separación de categoría idéntica a productos_seleccionados.xlsx
                if cat_nombre != last_cat_nombre:
                    cat_row = {"Código": cat_nombre, "Nombre": None}
                    if mostrar_cantidad:
                        cat_row["Cantidad"] = None
                    cat_row[nombre_columna_precio] = None
                    datos.append(cat_row)
                    last_cat_nombre = cat_nombre

                precio_val = calcular_precio_lista_regla(p, lista_seleccionada) if lista_seleccionada else float(p.precio or 0.0)
                fila = {
                    "Código": cod,
                    "Nombre": p.nombre
                }
                if mostrar_cantidad:
                    fila["Cantidad"] = p.cantidad
                fila[nombre_columna_precio] = precio_val
                datos.append(fila)

        df = pd.DataFrame(datos)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Productos')
            workbook = writer.book
            worksheet = writer.sheets['Productos']

            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#2c3e50',
                'font_color': 'white',
                'border': 1
            })
            cat_format = workbook.add_format({
                'bold': True,
                'bg_color': '#e2e8f0',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            money_format = workbook.add_format({
                'num_format': '$#,##0.00',
                'border': 1
            })

            worksheet.set_column('A:A', 18)
            worksheet.set_column('B:B', 50)
            worksheet.set_column('C:Z', 15)

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            for row_num, row_data in enumerate(df.values):
                excel_row = row_num + 1
                if pd.isna(row_data[1]):
                    cat_name = str(row_data[0])
                    worksheet.merge_range(excel_row, 0, excel_row, len(df.columns) - 1, cat_name, cat_format)

        output.seek(0)
        filename = f"lista_precios_{nombre_lista_archivo}.xlsx"
        return send_file(output, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    elif formato == "pdf":
        tasa_bcv = TasaCambio.query.filter_by(fuente='BCV').order_by(TasaCambio.id.desc()).first()
        tasa_usdt = TasaCambio.query.filter_by(fuente='BINANCE_USDT').order_by(TasaCambio.id.desc()).first()
        tasa_euro = TasaCambio.query.filter_by(fuente='BCV_EURO').order_by(TasaCambio.id.desc()).first()

        productos_pdf = []
        for orig in productos:
            p = copy.copy(orig)
            if lista_opcion != "todas":
                p.precio = calcular_precio_lista_regla(p, lista_seleccionada) if lista_seleccionada else float(p.precio or 0.0)
            productos_pdf.append(p)

        html = render_template('pdf_template.html',
                               productos=productos_pdf,
                               tasa_bcv=tasa_bcv,
                               tasa_usdt=tasa_usdt,
                               tasa_euro=tasa_euro,
                               fecha=datetime.now().strftime("%d/%m/%Y"),
                               mostrar_margenes=False,
                               moneda_publico='usd',
                               mostrar_cantidad=mostrar_cantidad)

        pdf_io = io.BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_io)
        if pisa_status.err:
            flash("Error al generar PDF", "danger")
            return redirect(url_for("inventario.lista_precios"))

        pdf_io.seek(0)
        filename = f"lista_precios_{nombre_lista_archivo}.pdf"
        return send_file(pdf_io, download_name=filename, as_attachment=True, mimetype='application/pdf')


@inventario_bp.route("/productos")
def productos():
    # Parámetros de búsqueda y paginación
    page = request.args.get('page', 1, type=int)
    query_str = request.args.get('q', '').strip()
    eliminados = request.args.get('eliminados', '0')
    categorias_id = request.args.getlist('categoria_id')
    categorias_id = [c for c in categorias_id if c] # Eliminar vacíos
    estado_stock = request.args.get('estado_stock', '')
    es_dropshipping = request.args.get('es_dropshipping', '')
    sort_by = request.args.get('sort_by', '')
    order = request.args.get('order', 'asc')
    
    if eliminados == '1' and current_user.rol.nombre in ['Super Admin', 'Administrador']:
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
        
    if categorias_id:
        query = query.filter(Productos.categoria_id.in_(categorias_id))
        
    if estado_stock:
        if estado_stock == 'sin_stock':
            query = query.filter(Productos.cantidad == 0)
        elif estado_stock == 'bajo_stock':
            query = query.filter(Productos.cantidad > 0, Productos.cantidad <= 5)
        elif estado_stock == 'suficiente':
            query = query.filter(Productos.cantidad > 5)

    if es_dropshipping == 'si':
        query = query.filter(Productos.es_dropshipping == True)
    elif es_dropshipping == 'no':
        query = query.filter((Productos.es_dropshipping == False) | (Productos.es_dropshipping == None))

    # Ordenamiento
    if sort_by == 'stock':
        if order == 'desc':
            query = query.order_by(Productos.cantidad.desc())
        else:
            query = query.order_by(Productos.cantidad.asc())
    elif sort_by == 'precio':
        if order == 'desc':
            query = query.order_by(Productos.precio.desc())
        else:
            query = query.order_by(Productos.precio.asc())
    elif sort_by == 'margen':
        margen_expr = (Productos.precio - db.func.coalesce(Productos.costo, 0))
        if order == 'desc':
            query = query.order_by(margen_expr.desc())
        else:
            query = query.order_by(margen_expr.asc())
    else:
        from models import Categorias
        # Ordenado por categoría y luego alfabéticamente
        query = query.outerjoin(Categorias, Productos.categoria_id == Categorias.id).order_by(Categorias.nombre.asc(), Productos.nombre.asc())

    productos_paginados = query.paginate(page=page, per_page=50, error_out=False)
    
    # Obtenemos las últimas tasas registradas
    tasa_bcv = TasaCambio.query.filter_by(fuente='BCV').order_by(TasaCambio.id.desc()).first()
    tasa_euro = TasaCambio.query.filter_by(fuente='BCV_EURO').order_by(TasaCambio.id.desc()).first()
    tasa_usdt = TasaCambio.query.filter_by(fuente='BINANCE_USDT').order_by(TasaCambio.id.desc()).first()

    from models import Categorias, ListasPrecios
    categorias = Categorias.query.filter_by(deleted_at=None).order_by(Categorias.nombre).all()
    listas_precios = ListasPrecios.query.filter_by(activa=True).all()

    # Le pasamos la lista y las tasas al HTML
    return render_template('dashboard.html', 
                           productos=productos_paginados, 
                           tasa_bcv=tasa_bcv, 
                           tasa_euro=tasa_euro,
                           tasa_usdt=tasa_usdt,
                           query_str=query_str,
                           eliminados=eliminados,
                           categorias=categorias,
                           categorias_id=categorias_id,
                           estado_stock=estado_stock,
                           es_dropshipping=es_dropshipping,
                           sort_by=sort_by,
                           order=order,
                           listas_precios=listas_precios)



@inventario_bp.route("/descargar-pdf")
def descargar_pdf():
    import uuid
    import threading
    import os
    from flask import current_app, flash, redirect, url_for
    from flask_login import current_user
    
    if not current_user.is_authenticated:
        flash("Debes iniciar sesión para realizar esta acción.", "danger")
        return redirect(url_for("auth.login"))

    app_obj = current_app._get_current_object()
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"Reporte_Inventario_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
    
    def run_pdf_generation(app, fname, user_id):
        with app.app_context():
            from extensions import db
            from models import Productos, TasaCambio, Notificacion
            import os
            from xhtml2pdf import pisa
            from flask import render_template
            
            try:
                # 1. Traemos los datos de la base de datos
                from models import Categorias
                lista_productos = Productos.query.filter_by(deleted_at=None).outerjoin(Categorias, Productos.categoria_id == Categorias.id).order_by(Categorias.nombre.asc(), Productos.nombre.asc()).all()
                tasa_bcv = TasaCambio.query.filter_by(fuente='BCV').order_by(TasaCambio.id.desc()).first()
                fecha_actual = datetime.now().strftime("%d/%m/%Y")

                # 2. Renderizamos la plantilla HTML secreta del PDF (en texto)
                html_renderizado = render_template('pdf_template.html', 
                                                   productos=lista_productos, 
                                                   tasa_bcv=tasa_bcv, 
                                                   fecha=fecha_actual,
                                                   moneda_publico='ambas')

                # 3. Guardar el PDF a disco
                upload_folder = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                filepath = os.path.join(upload_folder, fname)
                
                with open(filepath, "w+b") as dest_pdf:
                    pisa_status = pisa.CreatePDF(html_renderizado, dest=dest_pdf)
                
                if pisa_status.err:
                    raise Exception("Error interno al generar PDF con xhtml2pdf")
                
                # 4. Crear notificación de éxito
                mensaje = f"El reporte de inventario está listo. <a href='/descargas/{fname}' target='_blank' class='fw-bold text-primary text-decoration-underline'>Descargar PDF</a>"
                notif = Notificacion(usuario_id=user_id, mensaje=mensaje, tipo='success')
            except Exception as e:
                print(f"Error generando PDF asincrono: {e}")
                notif = Notificacion(usuario_id=user_id, mensaje="Hubo un error al generar el PDF del inventario.", tipo='danger')
                
            db.session.add(notif)
            db.session.commit()
            
    # Iniciar el hilo en segundo plano
    t = threading.Thread(target=run_pdf_generation, args=(app_obj, filename, current_user.id))
    t.start()
    
    flash("El reporte se está generando en segundo plano. Recibirás una notificación en la campanita cuando esté listo para descargar.", "info")
    return redirect(url_for("inventario.productos"))

@inventario_bp.route("/descargas/<filename>")
def descargar_archivo(filename):
    from flask import send_from_directory, current_app, flash, redirect, url_for
    from flask_login import current_user
    import os
    
    if not current_user.is_authenticated:
        flash("Debes iniciar sesión para descargar archivos.", "danger")
        return redirect(url_for("auth.login"))
        
    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
    return send_from_directory(upload_folder, filename, as_attachment=True)

  
@inventario_bp.route("/importar", methods=["GET", "POST"])
@rol_requerido('Administrador', 'Supervisor')
def importar_excel():
  # Instanciamos el escudo de seguridad (formulario) que creaste
  form = CargaMasivaForm()

  # Si el usuario hace clic en enviar y el archivo es seguro (.csv o .xlsx)
  if form.validate_on_submit():
    archivo = form.archivo.data
    
    import os
    import uuid
    import threading
    from flask import current_app
    
    # 1. Guardar el archivo en disco para el hilo en segundo plano
    filename = f"{uuid.uuid4()}_{archivo.filename}"
    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    archivo.save(filepath)
    
    # 2. Definir función en segundo plano
    def run_import(app, path_archivo, id_usuario):
        with app.app_context():
            from extensions import db
            from models import Notificacion
            
            exito = False
            mensaje_notif = "Error desconocido."
            try:
                from services.inventario_service import procesar_carga_masiva
                exito, mensaje_notif = procesar_carga_masiva(path_archivo)
            except Exception as e:
                mensaje_notif = f"Error en procesamiento: {str(e)}"
                print(mensaje_notif)
            finally:
                if os.path.exists(path_archivo):
                    os.remove(path_archivo)
                    
                # Crear notificación para el usuario
                notif = Notificacion(
                    usuario_id=id_usuario,
                    mensaje=f"Carga masiva finalizada. {mensaje_notif}",
                    tipo='success' if exito else 'danger'
                )
                db.session.add(notif)
                db.session.commit()
                    
    # 3. Iniciar el hilo
    app_obj = current_app._get_current_object()
    t = threading.Thread(target=run_import, args=(app_obj, filepath, current_user.id))
    t.start()
    
    flash("El archivo es grande y se está procesando en segundo plano. Esto evitará que la página se cuelgue. Los productos irán apareciendo en el inventario durante los próximos minutos.", "info")
    return redirect(url_for("inventario.productos"))
    
  elif request.method == 'POST':
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"Error en el campo '{field}': {error}", "danger")

  # Si el usuario solo entra a la URL (GET), mostramos texto temporal
  # En la fase 7 reemplazaremos esto por una página web real (HTML)

  # Si el usuario solo entra a la URL (GET), mostramos texto temporal
  # En la fase 7 reemplazaremos esto por una página web real (HTML)
  return render_template('importar.html', form=form)

# ==========================================
# RUTAS DE CRUD MANUAL (Crear, Editar, Borrar)
# ==========================================
from forms import ProductosForm
from models import Categorias, Atributos, ValoresAtributos, Configuracion
from models import Inventario, Productos, TasaCambio, Contactos

def cargar_opciones_form(form):
    """Ayudante para cargar las opciones de Categorías y Proveedores desde la BD"""
    # Categorías
    form.categoria_id.choices = [(0, "Sin Categoría")] + [(c.id, c.nombre) for c in Categorias.query.filter_by(deleted_at=None).order_by('nombre').all()]
    # Proveedores
    form.proveedor_id.choices = [(0, "Sin Proveedor Predeterminado")] + [(p.id, f"{p.identificacion} - {p.nombre}") for p in Contactos.query.order_by('nombre').all()]

@inventario_bp.route("/productos/nuevo", methods=["GET", "POST"])
@rol_requerido('Administrador', 'Supervisor')
def nuevo_producto():
    form = ProductosForm()
    cargar_opciones_form(form)
    
    from models import ListasPrecios, ProductoPrecios
    if form.validate_on_submit():
        nuevo_prod = Productos(
            nombre=form.nombre.data,
            cantidad=form.cantidad.data,
            precio=form.precio.data,
            costo=form.costo.data,
            descripcion=form.descripcion.data,
            categoria_id=form.categoria_id.data if (form.categoria_id.data and form.categoria_id.data > 0) else None,
            es_dropshipping=form.es_dropshipping.data if (Configuracion.query.filter_by(clave="modulo_dropshipping_activo").first() and Configuracion.query.filter_by(clave="modulo_dropshipping_activo").first().valor.lower() in ['true', '1', 'si']) else False,
            proveedor_id=form.proveedor_id.data if (form.proveedor_id.data and form.proveedor_id.data > 0) else None
        )
        
        # Guardar Atributos dinámicos
        valores_ids = request.form.getlist('valores[]')
        for v_id in valores_ids:
            if v_id:
                valor_obj = ValoresAtributos.query.get(v_id)
                if valor_obj:
                    nuevo_prod.valores.append(valor_obj)
                
        db.session.add(nuevo_prod)
        db.session.flush() # Para obtener nuevo_prod.id
        
        listas_precios = ListasPrecios.query.filter_by(activa=True).all()
        for lista in listas_precios:
            precio_lista_str = request.form.get(f'precio_lista_{lista.id}')
            if precio_lista_str and precio_lista_str.strip() != '':
                try:
                    precio_val = float(precio_lista_str)
                    prod_precio = ProductoPrecios(producto_id=nuevo_prod.id, lista_id=lista.id, precio=precio_val)
                    db.session.add(prod_precio)
                except ValueError:
                    pass
        
        db.session.commit()
        flash("Producto creado exitosamente", "success")
        return redirect(url_for("inventario.productos"))
        
    if request.method == "POST" and not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                field_label = getattr(form, field).label.text if hasattr(form, field) and hasattr(getattr(form, field), 'label') else field
                flash(f"{field_label}: {error}", "danger")

    todos_atributos = Atributos.query.filter_by(deleted_at=None).order_by('nombre').all()
    listas_precios = ListasPrecios.query.filter_by(activa=True).all()
    return render_template("producto_form.html", form=form, es_edicion=False, atributos=todos_atributos, producto_valores=[], listas_precios=listas_precios)

@inventario_bp.route("/productos/editar/<int:id>", methods=["GET", "POST"])
@rol_requerido('Administrador', 'Supervisor')
def editar_producto(id):
    producto = Productos.query.get_or_404(id)
    form = ProductosForm(obj=producto)
    
    # Manejar combos
    if request.method == "GET":
        if producto.categoria_id is None:
            form.categoria_id.data = 0
        if producto.proveedor_id is None:
            form.proveedor_id.data = 0
        
    cargar_opciones_form(form)

    if form.validate_on_submit():
        stock_anterior = producto.cantidad
        nuevo_stock = form.cantidad.data
        
        producto.nombre = form.nombre.data
        producto.cantidad = nuevo_stock
        producto.precio = form.precio.data
        producto.costo = form.costo.data
        producto.descripcion = form.descripcion.data
        producto.categoria_id = form.categoria_id.data if (form.categoria_id.data and form.categoria_id.data > 0) else None
        conf_ds = Configuracion.query.filter_by(clave="modulo_dropshipping_activo").first()
        modulo_ds_activo = (conf_ds.valor.lower() in ['true', '1', 'si']) if conf_ds else False
        producto.es_dropshipping = form.es_dropshipping.data if modulo_ds_activo else False
        producto.proveedor_id = form.proveedor_id.data if (form.proveedor_id.data and form.proveedor_id.data > 0) else None
        
        if stock_anterior != nuevo_stock:
            from models import Transacciones
            from datetime import datetime
            diferencia = nuevo_stock - stock_anterior
            tipo_movimiento = 'Ajuste de entrada' if diferencia > 0 else 'Ajuste de salida'
            referencia_ajm = f"AJM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            transaccion = Transacciones(
                producto_id=producto.id,
                tipo=tipo_movimiento,
                cantidad=abs(diferencia),
                stock_anterior=stock_anterior,
                fecha=datetime.now().date(),
                referencia=referencia_ajm
            )
            db.session.add(transaccion)
        
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
                    
        # Listas de Precios
        from models import ListasPrecios, ProductoPrecios
        listas_precios = ListasPrecios.query.filter_by(activa=True).all()
        for lista in listas_precios:
            precio_lista_str = request.form.get(f'precio_lista_{lista.id}')
            prod_precio = ProductoPrecios.query.filter_by(producto_id=producto.id, lista_id=lista.id).first()
            
            if precio_lista_str and precio_lista_str.strip() != '':
                try:
                    precio_val = float(precio_lista_str)
                    if not prod_precio:
                        prod_precio = ProductoPrecios(producto_id=producto.id, lista_id=lista.id)
                        db.session.add(prod_precio)
                    prod_precio.precio = precio_val
                except ValueError:
                    pass
            else:
                if prod_precio:
                    db.session.delete(prod_precio)
        
        db.session.commit()
        flash("Producto actualizado exitosamente", "success")
        return redirect(url_for("inventario.productos"))
        
    if request.method == "POST" and not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                field_label = getattr(form, field).label.text if hasattr(form, field) and hasattr(getattr(form, field), 'label') else field
                flash(f"{field_label}: {error}", "danger")

    # Obtener valores actuales para mostrarlos en la UI (array de IDs de valores)
    valores_actuales = [{"atributo_id": v.atributo_id, "valor_id": v.id} for v in producto.valores]
    todos_atributos = Atributos.query.filter_by(deleted_at=None).order_by('nombre').all()
    
    from models import ListasPrecios, ProductoPrecios
    listas_precios = ListasPrecios.query.filter_by(activa=True).all()
    precios_dict = {}
    if es_edicion := True:
        alts = ProductoPrecios.query.filter_by(producto_id=producto.id).all()
        precios_dict = {alt.lista_id: float(alt.precio) for alt in alts}
    
    return render_template("producto_form.html", form=form, es_edicion=True, producto=producto, atributos=todos_atributos, producto_valores=valores_actuales, listas_precios=listas_precios, precios_dict=precios_dict)

@inventario_bp.route("/productos/eliminar/<int:id>", methods=["POST"])
@rol_requerido('Administrador')
def eliminar_producto(id):
    producto = Productos.query.filter_by(id=id, deleted_at=None).first_or_404()
    # Soft delete: En lugar de destruir, marcamos la fecha de eliminación
    producto.deleted_at = datetime.now()
    db.session.commit()
    flash("Producto enviado a la papelera correctamente", "success")
    return redirect(url_for("inventario.productos"))

@inventario_bp.route("/productos/restaurar/<int:id>", methods=["POST"])
@rol_requerido('Administrador')
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
@rol_requerido('Administrador', 'Supervisor')
def historial_transacciones():
    page = request.args.get('page', 1, type=int)
    
    # Parámetros de filtro extraídos para enviarlos al template y mantenerlos en los inputs
    q = request.args.get('q', '').strip()
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()
    tipo = request.args.get('tipo', '').strip()
    
    # Delegamos toda la lógica de filtrado a nuestro servicio
    transacciones_paginadas = obtener_historial_filtrado(request.args, page)
    
    return render_template("transacciones.html", transacciones=transacciones_paginadas, q=q, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, tipo=tipo)

@inventario_bp.route("/productos/accion-masiva", methods=["POST"])
@rol_requerido('Administrador')
def accion_masiva_productos():
    ids_str = request.form.get("ids_seleccionados", "")
    accion = request.form.get("accion", "")
    from models import Categorias
    query = Productos.query
    
    if "all" in accion:
        query = query.filter_by(deleted_at=None)
        
        # Aplicar los filtros de la vista actual
        q = request.form.get("q", "")
        estado_stock = request.form.get("estado_stock", "")
        es_dropshipping = request.form.get("es_dropshipping", "")
        categorias_id_str = request.form.get("categoria_id", "")
        
        if q:
            query = query.filter(Productos.nombre.ilike(f"%{q}%") | Productos.descripcion.ilike(f"%{q}%"))
            
        if estado_stock:
            if estado_stock == 'sin_stock':
                query = query.filter(Productos.cantidad <= 0)
            elif estado_stock == 'bajo_stock':
                query = query.filter(Productos.cantidad > 0, Productos.cantidad <= 5)
            elif estado_stock == 'suficiente':
                query = query.filter(Productos.cantidad > 5)
                
        if es_dropshipping:
            if es_dropshipping == 'si':
                query = query.filter(Productos.es_dropshipping == True)
            elif es_dropshipping == 'no':
                query = query.filter((Productos.es_dropshipping == False) | (Productos.es_dropshipping == None))
                
        if categorias_id_str:
            lista_cat = [int(i) for i in categorias_id_str.split(",") if i.strip()]
            if lista_cat:
                query = query.filter(Productos.categoria_id.in_(lista_cat))
    else:
        if not ids_str:
            flash("No se seleccionaron productos.", "warning")
            return redirect(url_for("inventario.productos"))
            
        lista_ids = [int(i) for i in ids_str.split(",")]
        query = query.filter(Productos.id.in_(lista_ids))
        
    from sqlalchemy.orm import joinedload
    query = query.outerjoin(Categorias, Productos.categoria_id == Categorias.id).options(joinedload(Productos.precios_alternativos)).order_by(Categorias.nombre.asc(), Productos.nombre.asc())
    productos = query.all()
    
    mostrar_cantidad = request.form.get("mostrar_cantidad") == "si"
    
    if accion == "delete":
        for p in productos:
            p.deleted_at = datetime.now()
        db.session.commit()
        flash(f"{len(productos)} productos eliminados correctamente.", "success")
        return redirect(url_for("inventario.productos"))
        
    elif "excel" in accion:
        import pandas as pd
        import io
        from flask import send_file
        
        mostrar_margenes = "interno" in accion
        moneda_publico = "usd" if "usd" in accion else ("bs" if "bs" in accion else ("usdt" if "usdt" in accion else ("euro" if "euro" in accion else "ambas")))
        
        tasa_bcv = TasaCambio.query.filter_by(fuente='BCV').order_by(TasaCambio.id.desc()).first()
        tasa_usdt = TasaCambio.query.filter_by(fuente='BINANCE_USDT').order_by(TasaCambio.id.desc()).first()
        tasa_euro = TasaCambio.query.filter_by(fuente='BCV_EURO').order_by(TasaCambio.id.desc()).first()
        
        lista_id_export = request.form.get("lista_precio_export", "base")
        lista_export = None
        if lista_id_export != "base":
            from models import ListasPrecios
            lista_export = ListasPrecios.query.get(lista_id_export)
            
        def calcular_precio_lista(p, lista):
            if not lista: return float(p.precio)
            for alt in p.precios_alternativos:
                if alt.lista_id == lista.id:
                    return float(alt.precio)
            base_calc = float(p.precio) if lista.basado_en == 'precio_base' else float(p.costo or 0)
            if lista.tipo == 'Porcentaje':
                mod = base_calc * (float(lista.valor_regla) / 100.0)
                return round(base_calc + mod if lista.operador == '+' else base_calc - mod, 2)
            elif lista.tipo == 'Monto Fijo':
                mod = float(lista.valor_regla)
                return round(base_calc + mod if lista.operador == '+' else base_calc - mod, 2)
            return float(p.precio)
        
        datos = []
        last_cat_nombre = None
        for p in productos:
            cat_nombre = p.categoria.nombre if p.categoria else "SIN CATEGORÍA"
            
            if cat_nombre != last_cat_nombre:
                # Add category header row
                cat_row = {
                    "Código": "",
                    "Nombre": f"=== {cat_nombre.upper()} ==="
                }
                if mostrar_cantidad:
                    cat_row["Cantidad"] = ""
                if not moneda_publico or moneda_publico in ['usd', 'ambas'] or mostrar_margenes:
                    cat_row["Precio ($)"] = ""
                if not moneda_publico or moneda_publico in ['bs', 'ambas'] or mostrar_margenes:
                    cat_row["Precio (Bs)"] = ""
                if not moneda_publico or moneda_publico in ['usdt', 'ambas'] or mostrar_margenes:
                    cat_row["Precio (USDT)"] = ""
                if not moneda_publico or moneda_publico in ['euro', 'ambas'] or mostrar_margenes:
                    cat_row["Precio (Euro)"] = ""
                if mostrar_margenes:
                    cat_row.update({
                        "Costo ($)": "",
                        "Margen ($)": "",
                        "Margen BCV (Bs)": "",
                        "Margen USDT (Bs)": ""
                    })
                datos.append(cat_row)
                last_cat_nombre = cat_nombre

            precio = calcular_precio_lista(p, lista_export)
            precio_bs = float(precio * float(tasa_bcv.tasa)) if tasa_bcv else 0
            precio_usdt = round(float(precio_bs / float(tasa_usdt.tasa)), 2) if (tasa_usdt and float(tasa_usdt.tasa) > 0) else 0
            precio_euro = round(float(precio_bs / float(tasa_euro.tasa)), 2) if (tasa_euro and float(tasa_euro.tasa) > 0) else 0
            
            fila = {
                "Código": p.descripcion.replace("CÓDIGO: ", ""),
                "Nombre": p.nombre
            }
            if mostrar_cantidad:
                fila["Cantidad"] = p.cantidad
            
            if not moneda_publico or moneda_publico in ['usd', 'ambas'] or mostrar_margenes:
                fila["Precio ($)"] = precio
            if not moneda_publico or moneda_publico in ['bs', 'ambas'] or mostrar_margenes:
                fila["Precio (Bs)"] = precio_bs
            if not moneda_publico or moneda_publico in ['usdt', 'ambas'] or mostrar_margenes:
                fila["Precio (USDT)"] = precio_usdt
            if not moneda_publico or moneda_publico in ['euro', 'ambas'] or mostrar_margenes:
                fila["Precio (Euro)"] = precio_euro
            
            if mostrar_margenes:
                costo = float(p.costo or 0)
                margen_usd = precio - costo
                margen_bcv = margen_usd * float(tasa_bcv.tasa) if tasa_bcv else 0
                margen_usdt = margen_usd * float(tasa_usdt.tasa) if tasa_usdt else 0
                
                fila_con_margenes = {
                    "Código": fila["Código"],
                    "Nombre": fila["Nombre"]
                }
                if mostrar_cantidad:
                    fila_con_margenes["Cantidad"] = fila["Cantidad"]
                
                fila_con_margenes.update({
                    "Costo ($)": costo,
                    "Precio ($)": precio,
                    "Margen ($)": margen_usd,
                    "Margen BCV (Bs)": margen_bcv,
                    "Margen USDT (Bs)": margen_usdt
                })
                fila = fila_con_margenes
            
            datos.append(fila)
            
        df = pd.DataFrame(datos)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Productos')
            workbook = writer.book
            worksheet = writer.sheets['Productos']
            
            # Formatos
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#2c3e50',
                'font_color': 'white',
                'border': 1
            })
            cat_format = workbook.add_format({
                'bold': True,
                'bg_color': '#e2e8f0',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            
            # Anchos de columna
            worksheet.set_column('A:A', 15)
            worksheet.set_column('B:B', 50)
            worksheet.set_column('C:C', 12)
            worksheet.set_column('D:K', 15)
            
            # Aplicar formato a la fila de encabezado
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
            # Identificar filas de categoría y combinarlas
            for row_num, row_data in enumerate(df.values):
                # row_num + 1 porque la fila 0 de excel es el encabezado
                excel_row = row_num + 1
                if not row_data[0]:  # Si Código está vacío, es una fila de categoría
                    cat_name = str(row_data[1]).replace("=== ", "").replace(" ===", "")
                    # merge_range(first_row, first_col, last_row, last_col, data, cell_format)
                    worksheet.merge_range(excel_row, 0, excel_row, len(df.columns) - 1, cat_name, cat_format)
        output.seek(0)
        
        nombre_archivo = "productos_catalogo_completo.xlsx" if "all" in accion else "productos_seleccionados.xlsx"
        return send_file(output, download_name=nombre_archivo, as_attachment=True)
        
    elif "pdf" in accion:
        import io
        from flask import send_file
        from xhtml2pdf import pisa
        
        mostrar_margenes = "interno" in accion
        moneda_publico = "usd" if "usd" in accion else ("bs" if "bs" in accion else ("usdt" if "usdt" in accion else ("euro" if "euro" in accion else "ambas")))
        
        tasa_bcv = TasaCambio.query.filter_by(fuente='BCV').order_by(TasaCambio.id.desc()).first()
        tasa_usdt = TasaCambio.query.filter_by(fuente='BINANCE_USDT').order_by(TasaCambio.id.desc()).first()
        tasa_euro = TasaCambio.query.filter_by(fuente='BCV_EURO').order_by(TasaCambio.id.desc()).first()
        
        lista_id_export = request.form.get("lista_precio_export", "base")
        lista_export = None
        if lista_id_export != "base":
            from models import ListasPrecios
            lista_export = ListasPrecios.query.get(lista_id_export)
            
        def calcular_precio_lista(p, lista):
            if not lista: return float(p.precio)
            for alt in p.precios_alternativos:
                if alt.lista_id == lista.id:
                    return float(alt.precio)
            base_calc = float(p.precio) if lista.basado_en == 'precio_base' else float(p.costo or 0)
            if lista.tipo == 'Porcentaje':
                mod = base_calc * (float(lista.valor_regla) / 100.0)
                return round(base_calc + mod if lista.operador == '+' else base_calc - mod, 2)
            elif lista.tipo == 'Monto Fijo':
                mod = float(lista.valor_regla)
                return round(base_calc + mod if lista.operador == '+' else base_calc - mod, 2)
            return float(p.precio)
            
        # Overwrite p.precio temporarily just for rendering
        for p in productos:
            p.precio = calcular_precio_lista(p, lista_export)
            
        html = render_template('pdf_template.html', productos=productos, tasa_bcv=tasa_bcv, tasa_usdt=tasa_usdt, tasa_euro=tasa_euro, fecha=datetime.now().strftime("%d/%m/%Y"), mostrar_margenes=mostrar_margenes, moneda_publico=moneda_publico, mostrar_cantidad=mostrar_cantidad)
        
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

@inventario_bp.route('/productos/actualizar_stock_inline', methods=['POST'])
@rol_requerido('Administrador')
def actualizar_stock_inline():
    data = request.get_json()
    producto_id = data.get('producto_id')
    nuevo_stock = data.get('nuevo_stock')

    if producto_id is None or nuevo_stock is None:
        return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

    try:
        nuevo_stock = int(nuevo_stock)
        if nuevo_stock < 0:
            return jsonify({'success': False, 'message': 'El stock no puede ser negativo'}), 400
    except ValueError:
        return jsonify({'success': False, 'message': 'El stock debe ser un número entero'}), 400

    producto = Productos.query.get_or_404(producto_id)
    stock_anterior = producto.cantidad

    if stock_anterior == nuevo_stock:
        return jsonify({'success': True, 'message': 'El stock no ha cambiado', 'nuevo_stock': nuevo_stock})

    producto.cantidad = nuevo_stock
    db.session.commit()

    # Registrar la transacción
    from models import Transacciones
    from datetime import datetime
    diferencia = nuevo_stock - stock_anterior
    tipo_movimiento = 'Ajuste de entrada' if diferencia > 0 else 'Ajuste de salida'
    referencia_ajm = f"AJM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    transaccion = Transacciones(
        producto_id=producto.id,
        tipo=tipo_movimiento,
        cantidad=abs(diferencia),
        stock_anterior=stock_anterior,
        fecha=datetime.now().date(),
        referencia=referencia_ajm
    )
    db.session.add(transaccion)
    
    # Crear notificación
    from models import Notificacion
    notificacion = Notificacion(
        mensaje=f"Stock ajustado: {producto.nombre} pasó de {stock_anterior} a {nuevo_stock} (Usuario: {current_user.username})",
        leida=False,
        usuario_id=None # Null para global (todos los admins verán esto)
    )
    db.session.add(notificacion)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Stock actualizado correctamente',
        'nuevo_stock': nuevo_stock
    })
