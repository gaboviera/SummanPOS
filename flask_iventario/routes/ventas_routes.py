from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from extensions import db
from models import Productos, Atributos, GuiaDespacho, Transacciones, Contactos
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from flask_login import login_required, current_user

from services.ventas_service import procesar_nueva_venta

ventas_bp = Blueprint("ventas", __name__)

@ventas_bp.route("/ventas", methods=["GET"])
@login_required
def index():
    import json
    from models import Contactos, Productos, ListasPrecios, TasaCambio
    
    contactos = Contactos.query.filter_by(deleted_at=None).all()
    prov_list = [{'id': p.id, 'nombre': p.nombre} for p in contactos]
    
    listas = ListasPrecios.query.filter_by(activa=True).order_by(ListasPrecios.nombre).all()
    
    tasa_bcv = TasaCambio.query.filter_by(fuente='BCV').order_by(TasaCambio.id.desc()).first()
    tasa_usdt = TasaCambio.query.filter_by(fuente='BINANCE_USDT').order_by(TasaCambio.id.desc()).first()
    tasa_euro = TasaCambio.query.filter_by(fuente='BCV_EURO').order_by(TasaCambio.id.desc()).first()

    # El campo Vendedor(a) se rellenaba con current_user.username, que en esta
    # instalación es un correo, y ese texto es el que acababa impreso en la guía.
    # Se resuelve contra Contactos para guardar el nombre real desde el origen.
    vendedor_predeterminado = current_user.username
    contacto_vendedor = Contactos.query.filter(
        Contactos.correo.ilike(current_user.username)).first()
    if contacto_vendedor and contacto_vendedor.nombre:
        vendedor_predeterminado = contacto_vendedor.nombre

    return render_template("ventas.html", 
                           contactos=contactos, 
                           vendedor_predeterminado=vendedor_predeterminado, 
                           proveedores_json=json.dumps(prov_list), 
                           listas_precios=listas, 
                           tasa_bcv=tasa_bcv,
                           tasa_usdt=tasa_usdt,
                           tasa_euro=tasa_euro)

@ventas_bp.route("/api/productos", methods=["GET"])
@login_required
def api_obtener_productos():
    from models import ListasPrecios
    productos = Productos.query.options(
        joinedload(Productos.valores),
        joinedload(Productos.proveedor),
        joinedload(Productos.precios_alternativos)
    ).filter(
        db.or_(Productos.cantidad > 0, Productos.es_dropshipping == True),
        Productos.deleted_at == None
    ).all()

    lista_productos = []
    attr_marca = Atributos.query.filter_by(nombre="Marca").first()
    attr_marca_id = attr_marca.id if attr_marca else None
    
    listas_activas = ListasPrecios.query.filter_by(activa=True).all()
    
    from models import TasaCambio
    tasa_bcv = TasaCambio.query.filter_by(fuente='BCV').order_by(TasaCambio.id.desc()).first()
    tasa_usdt = TasaCambio.query.filter_by(fuente='BINANCE_USDT').order_by(TasaCambio.id.desc()).first()
    tasa_euro = TasaCambio.query.filter_by(fuente='BCV_EURO').order_by(TasaCambio.id.desc()).first()

    for p in productos:
        marca = "Generica"
        if attr_marca_id:
            marca_val = next((v for v in p.valores if v.atributo_id == attr_marca_id), None)
            if marca_val:
                marca = marca_val.valor
                
        precio_base = float(p.precio)
        costo = float(p.costo) if p.costo else 0.0
        
        precios_dict = {"base": precio_base}
        
        precio_bs = precio_base * float(tasa_bcv.tasa) if tasa_bcv else 0
        precios_dict["bs"] = round(precio_bs, 2)
        precios_dict["usdt"] = round(precio_bs / float(tasa_usdt.tasa), 2) if (tasa_usdt and float(tasa_usdt.tasa) > 0) else 0
        precios_dict["euro"] = round(precio_bs / float(tasa_euro.tasa), 2) if (tasa_euro and float(tasa_euro.tasa) > 0) else 0
        
        overrides = {alt.lista_id: float(alt.precio) for alt in p.precios_alternativos}
        
        for lista in listas_activas:
            if lista.id in overrides:
                precios_dict[str(lista.id)] = overrides[lista.id]
                continue
                
            base_calc = precio_base if lista.basado_en == 'precio_base' else costo
            val_usd = base_calc
            if lista.tipo == 'Porcentaje':
                mod = base_calc * (float(lista.valor_regla) / 100.0)
                val_usd = base_calc + mod if lista.operador == '+' else base_calc - mod
            elif lista.tipo == 'Monto Fijo':
                mod = float(lista.valor_regla)
                val_usd = base_calc + mod if lista.operador == '+' else base_calc - mod
                
            precios_dict[str(lista.id)] = round(val_usd, 2)
                
        lista_productos.append({
            "id": p.id,
            "codigo": p.descripcion.replace('CÓDIGO: ', '') if p.descripcion else "",
            "nombre": p.nombre,
            "marca": marca,
            "costo": costo,
            "precio": precio_base,
            "precios_listas": precios_dict,
            "stock": p.cantidad,
            "es_dropshipping": p.es_dropshipping or False,
            "proveedor_id": p.proveedor_id,
            "proveedor_nombre": p.proveedor.nombre if p.proveedor else "Sin Proveedor"
        })
    return jsonify(lista_productos)

@ventas_bp.route("/ventas/registrar", methods=["POST"])
@login_required
def registrar_venta():
    data = request.get_json()
    carrito = data.get("carrito", [])
    cliente = data.get("cliente", {})
    pago = data.get("pago", {})
    
    try:
        codigo_recibo = procesar_nueva_venta(cliente, carrito, pago)
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
    es_ajuste = referencia.startswith('AJM-')
    
    if es_ajuste:
        from types import SimpleNamespace
        guia = SimpleNamespace(
            cliente_nombre="N/A (Ajuste Manual)",
            cliente_direccion="N/A",
            vendedor_nombre=current_user.username if hasattr(current_user, 'username') else 'N/A',
            cliente_identificacion="N/A",
            cliente_telefono="N/A",
            ciudad="N/A",
            fecha=datetime.now(),
            referencia=referencia,
            observaciones="Ajuste manual de inventario",
            total=0
        )
    else:
        guia = GuiaDespacho.query.filter_by(referencia=ref_original).first_or_404()
        
    transacciones = Transacciones.query.filter_by(referencia=referencia).all()
    es_devolucion = referencia.startswith('DEV-')
    
    vendedor_telefono = ''
    # Lo que se imprime como Vendedor(a). Por defecto, lo que quedó guardado en
    # la guía; si ese valor se puede resolver contra Contactos, se usa el nombre
    # real. Así las guías viejas -que guardaron el usuario de la sesión, un
    # correo- también salen bien al reimprimirlas, sin migrar nada.
    vendedor_display = guia.vendedor_nombre
    if not es_ajuste:
        from models import Contactos
        from extensions import db

        ref_vendedor = (guia.vendedor_nombre or '').strip()
        contacto_vendedor = None
        if ref_vendedor:
            # Primero coincidencia EXACTA (ilike sin comodines). El '%...%' de
            # antes podía cruzar contactos distintos: "Ana" encaja dentro de
            # "Mariana". Se deja como último recurso.
            contacto_vendedor = (
                Contactos.query.filter(Contactos.correo.ilike(ref_vendedor)).first()
                or Contactos.query.filter(Contactos.nombre.ilike(ref_vendedor)).first()
                or Contactos.query.filter(db.or_(
                        Contactos.nombre.ilike(f'%{ref_vendedor}%'),
                        Contactos.correo.ilike(f'%{ref_vendedor}%')
                   )).first()
            )

        if contacto_vendedor:
            vendedor_telefono = contacto_vendedor.telefono
            if contacto_vendedor.nombre:
                vendedor_display = contacto_vendedor.nombre
        
        # Si la guía no tiene ciudad, buscar en el contacto del cliente
        if not guia.ciudad and guia.cliente_identificacion:
            contacto_cliente = Contactos.query.filter_by(identificacion=guia.cliente_identificacion).first()
            if contacto_cliente and contacto_cliente.ciudad:
                guia.ciudad = contacto_cliente.ciudad
            
    # Dos formatos de impresión, cada uno con su template y su geometría:
    #   con-encabezado -> recibo_encabezado.html: hoja normal, imprime los
    #                     datos del cliente en cada página, márgenes 2/2/1 cm
    #                     y una sola línea por producto (se recorta con "...").
    #   sin-encabezado -> recibo.html: hoja membretada fiscal, sin datos del
    #                     cliente, márgenes 7/4/2.54 cm.
    # El botón de la vista alterna entre ambos con ?formato=...
    formato = request.args.get('formato', 'con-encabezado')
    plantilla = 'recibo.html' if formato == 'sin-encabezado' else 'recibo_encabezado.html'

    return render_template(plantilla,
                           guia=guia,
                           transacciones=transacciones,
                           es_devolucion=es_devolucion,
                           es_ajuste=es_ajuste,
                           vendedor_telefono=vendedor_telefono,
                           vendedor_display=vendedor_display,
                           referencia=referencia,
                           formato=formato)

@ventas_bp.route("/ventas/recibo/<referencia>/excel", methods=["GET"])
@login_required
def exportar_recibo_excel(referencia):
    from flask import send_file
    from services.ventas_service import generar_recibo_excel

    ref_original = referencia.replace('DEV-', '')
    es_ajuste = referencia.startswith('AJM-')

    if es_ajuste:
        from types import SimpleNamespace
        guia = SimpleNamespace(
            cliente_nombre="N/A (Ajuste Manual)",
            cliente_direccion="N/A",
            vendedor_nombre=current_user.username if hasattr(current_user, 'username') else 'N/A',
            cliente_identificacion="N/A",
            cliente_telefono="N/A",
            ciudad="N/A",
            fecha=datetime.now(),
            referencia=referencia,
            observaciones="Ajuste manual de inventario",
            total=0,
            descuento_global=0,
            tasa_bcv=None
        )
    else:
        guia = GuiaDespacho.query.filter_by(referencia=ref_original).first_or_404()

    transacciones = Transacciones.query.filter_by(referencia=referencia).all()
    es_devolucion = referencia.startswith('DEV-')

    vendedor_telefono = ''
    vendedor_display = guia.vendedor_nombre
    if not es_ajuste:
        from models import Contactos
        from extensions import db

        ref_vendedor = (guia.vendedor_nombre or '').strip()
        contacto_vendedor = None
        if ref_vendedor:
            contacto_vendedor = (
                Contactos.query.filter(Contactos.correo.ilike(ref_vendedor)).first()
                or Contactos.query.filter(Contactos.nombre.ilike(ref_vendedor)).first()
                or Contactos.query.filter(db.or_(
                        Contactos.nombre.ilike(f'%{ref_vendedor}%'),
                        Contactos.correo.ilike(f'%{ref_vendedor}%')
                   )).first()
            )

        if contacto_vendedor:
            vendedor_telefono = contacto_vendedor.telefono or ''
            if contacto_vendedor.nombre:
                vendedor_display = contacto_vendedor.nombre

        if not guia.ciudad and guia.cliente_identificacion:
            contacto_cliente = Contactos.query.filter_by(identificacion=guia.cliente_identificacion).first()
            if contacto_cliente and contacto_cliente.ciudad:
                guia.ciudad = contacto_cliente.ciudad

    formato = request.args.get('formato', 'con-encabezado')
    output = generar_recibo_excel(
        guia=guia,
        transacciones=transacciones,
        es_devolucion=es_devolucion,
        es_ajuste=es_ajuste,
        vendedor_telefono=vendedor_telefono,
        vendedor_display=vendedor_display,
        formato=formato
    )

    # Lleva fecha y hora en el nombre a proposito: el navegador guarda cada
    # descarga con el mismo nombre y va agregando " (1)", " (2)"..., asi que
    # era muy facil abrir o imprimir una copia vieja creyendo que era la
    # recien generada. Con la marca de tiempo, la mas nueva se reconoce sola.
    filename = f"Recibo_{referencia}_{datetime.now().strftime('%Y-%m-%d_%H%M')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

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
        
    exportar = request.args.get('exportar', '')

    if exportar:
        todas_las_guias = query.order_by(GuiaDespacho.id.desc()).all()
        if exportar == 'excel':
            import pandas as pd
            import io
            from flask import send_file
            
            data = []
            for g in todas_las_guias:
                data.append({
                    "Nº Ticket": g.referencia,
                    "Fecha": (g.fecha - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M') if g.fecha else 'N/A',
                    "Cliente": g.cliente_nombre if g.cliente_nombre else 'Venta de Mostrador',
                    "Identificación": g.cliente_identificacion if g.cliente_identificacion else '',
                    "Vendedor": g.vendedor_nombre,
                    "Total ($)": g.total,
                    "Tasa BCV": g.tasa_bcv,
                    "Total (Bs)": (g.total * g.tasa_bcv) if g.total and g.tasa_bcv else 0.00,
                    "Estado": g.estado
                })
            df = pd.DataFrame(data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Historial Ventas')
            output.seek(0)
            return send_file(output, as_attachment=True, download_name=f'historial_ventas_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            
        elif exportar == 'pdf':
            import io
            from flask import send_file
            from xhtml2pdf import pisa
            
            for g in todas_las_guias:
                g.fecha_local = g.fecha - timedelta(hours=4) if g.fecha else None
            html_renderizado = render_template('pdf_ventas_historial.html', guias=todas_las_guias, fecha_generacion=datetime.now().strftime("%d/%m/%Y %H:%M"), q=q, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, estado=estado)
            pdf_en_memoria = io.BytesIO()
            pisa_status = pisa.CreatePDF(io.StringIO(html_renderizado), dest=pdf_en_memoria)
            pdf_en_memoria.seek(0)
            return send_file(pdf_en_memoria, as_attachment=True, download_name=f'historial_ventas_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf', mimetype='application/pdf')

    # Totalizadores
    todas_las_guias = query.all()
    total_usd = sum(g.total for g in todas_las_guias if g.total and g.estado != 'Anulada')
    total_bs = sum((g.total * g.tasa_bcv) for g in todas_las_guias if g.total and g.tasa_bcv and g.estado != 'Anulada')

    guias_paginadas = query.order_by(GuiaDespacho.id.desc()).paginate(page=page, per_page=20, error_out=False)
    
    for g in guias_paginadas.items:
        g.fecha_local = g.fecha - timedelta(hours=4) if g.fecha else None
        
    return render_template("historial_ventas.html", guias=guias_paginadas, q=q, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, estado=estado, total_usd=total_usd, total_bs=total_bs)

@ventas_bp.route("/api/ventas/<referencia>/detalles", methods=["GET"])
@login_required
def api_obtener_detalles(referencia):
    transacciones = Transacciones.query.filter_by(referencia=referencia).all()
    lista = []
    for t in transacciones:
        nombre = t.producto.nombre if t.producto else "Producto Eliminado"
        lista.append({
            "producto": nombre,
            "cantidad": t.cantidad,
            "tipo": t.tipo
        })
    return jsonify(lista)

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
