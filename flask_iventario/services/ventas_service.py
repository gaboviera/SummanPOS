import time
from datetime import datetime
from models import Productos, Transacciones, GuiaDespacho, TasaCambio, PagosCxC
from extensions import db
from services.contactos_service import asegurar_contacto_existente

def procesar_nueva_venta(cliente_data, carrito_data, pago_data=None):
    """
    Procesa toda la lógica de negocio de una venta:
    1. Asegura que el contacto exista (o lo crea)
    2. Valida el stock
    3. Crea la Guía de Despacho
    4. Descuenta el inventario y crea las Transacciones
    """
    if not carrito_data or len(carrito_data) == 0:
        raise ValueError("El carrito está vacío.")

    # Generamos un código único usando la hora exacta, ej: VTA-17098453
    codigo_recibo = f"VTA-{int(time.time())}"

    # 1. Asegurar que el contacto exista
    cliente_obj = asegurar_contacto_existente(cliente_data)

    # Buscar las tasas más recientes
    tasa_bcv_obj = TasaCambio.query.filter_by(fuente='BCV').order_by(TasaCambio.id.desc()).first()
    tasa_euro_obj = TasaCambio.query.filter_by(fuente='BCV_EURO').order_by(TasaCambio.id.desc()).first()
    tasa_usdt_obj = TasaCambio.query.filter_by(fuente='BINANCE_USDT').order_by(TasaCambio.id.desc()).first()
    
    val_bcv = tasa_bcv_obj.tasa if tasa_bcv_obj else None
    val_euro = tasa_euro_obj.tasa if tasa_euro_obj else None
    val_usdt = tasa_usdt_obj.tasa if tasa_usdt_obj else None

    if not pago_data:
        pago_data = {}
        
    tipo_pago = pago_data.get('tipo', 'Contado')
    dias_plazo = int(pago_data.get('dias_plazo', 0))
    lista_pagos = pago_data.get('pagos', [])
    
    total_abonado = sum(float(p['monto']) for p in lista_pagos)
    
    # We trust the total from the frontend since it already includes taxes, discounts, etc.
    # We could recalculate it here, but it's passed as total_pagar
    total_factura = float(cliente_data.get('total', 0)) 
    descuento_global = float(cliente_data.get('descuento_global', 0))
    
    estado_pago = 'Crédito' if tipo_pago == 'Crédito' else 'Pagada'
    
    fecha_vencimiento = None
    if estado_pago == 'Crédito' and dias_plazo > 0:
        import datetime as dt
        fecha_vencimiento = datetime.utcnow() + dt.timedelta(days=dias_plazo)

    # 2. Guardar la Cabecera de la Guía de Despacho
    nueva_guia = GuiaDespacho(
        referencia=codigo_recibo,
        fecha=datetime.utcnow(),
        cliente_nombre=cliente_data.get('nombre'),
        cliente_identificacion=cliente_data.get('identificacion'),
        cliente_direccion=cliente_data.get('direccion'),
        cliente_telefono=cliente_data.get('telefono'),
        ciudad=cliente_data.get('ciudad'),
        vendedor_nombre=cliente_data.get('vendedor'),
        observaciones=cliente_data.get('observaciones'),
        total=total_factura,
        descuento_global=descuento_global,
        tasa_bcv=val_bcv,
        tasa_euro=val_euro,
        tasa_usdt=val_usdt,
        estado_pago=estado_pago,
        monto_abonado=total_abonado,
        fecha_vencimiento=fecha_vencimiento
    )
    db.session.add(nueva_guia)
    db.session.flush() # Para obtener nueva_guia.id
    
    # Registrar los pagos iterando la lista_pagos
    for pago in lista_pagos:
        monto_p = float(pago.get('monto', 0))
        if monto_p > 0:
            metodo_str = pago.get('metodo', 'Efectivo')
            ref = pago.get('referencia', '')
            b_ori = pago.get('banco_origen', '')
            b_des = pago.get('banco_destino', '')
            
            tasa = pago.get('tasa_usada')
            moneda = pago.get('moneda_tasa')
            monto_moneda = pago.get('monto_moneda')

            ref_final = ref
            if b_ori or b_des:
                ref_final += f" | {b_ori} -> {b_des}"
                ref_final = ref_final.strip(' |')
                
            nuevo_pago = PagosCxC(
                guia_id=nueva_guia.id,
                fecha=datetime.utcnow(),
                monto=monto_p,
                metodo=metodo_str,
                referencia_pago=ref_final if ref_final else "N/A",
                tasa_usada=float(tasa) if tasa else None,
                moneda_tasa=moneda if moneda else None,
                monto_moneda=float(monto_moneda) if monto_moneda else None
            )
            db.session.add(nuevo_pago)

    # 3. Recorrer el Carrito y procesar (Físico vs Dropshipping por Proveedor)
    from models import OrdenDropshipping, DetalleDropshipping, Contactos
    dropshipping_por_proveedor = {}

    for item in carrito_data:
        producto = Productos.query.get(item['id'])
        if not producto:
            raise ValueError(f"Producto ID {item['id']} no encontrado.")

        cantidad_vender = int(item['cantidad'])
        from models import Configuracion
        conf_ds = Configuracion.query.filter_by(clave="modulo_dropshipping_activo").first()
        modulo_ds_activo = (conf_ds.valor.lower() in ['true', '1', 'si']) if conf_ds else False

        es_ds = False
        if modulo_ds_activo:
            es_ds = item.get('es_dropshipping', False) or getattr(producto, 'es_dropshipping', False)

        if es_ds:
            proveedor_id = item.get('proveedor_id') or producto.proveedor_id
            if not proveedor_id:
                prov_default = Contactos.query.filter_by(deleted_at=None).first()
                proveedor_id = prov_default.id if prov_default else None

            if not proveedor_id:
                raise ValueError(f"Debe seleccionar un proveedor para el producto de dropshipping '{producto.nombre}'.")

            if proveedor_id not in dropshipping_por_proveedor:
                dropshipping_por_proveedor[proveedor_id] = []

            costo_val = float(item.get('costo', producto.costo or 0.0))
            precio_val = float(item.get('precio', producto.precio))

            dropshipping_por_proveedor[proveedor_id].append({
                'producto': producto,
                'cantidad': cantidad_vender,
                'costo': costo_val,
                'precio': precio_val
            })

            # Registrar la transacción de venta para que aparezca en el Recibo / Guía de Despacho
            nueva_transaccion_ds = Transacciones(
                producto_id=producto.id,
                cantidad=cantidad_vender,
                fecha=datetime.utcnow(),
                tipo="Venta (Dropshipping)",
                stock_anterior=producto.cantidad,
                referencia=codigo_recibo,
                precio_unitario=precio_val,
                costo_unitario=costo_val
            )
            db.session.add(nueva_transaccion_ds)
        else:
            if producto.cantidad < cantidad_vender:
                raise ValueError(f"Stock insuficiente para {producto.nombre}. Disponible: {producto.cantidad}")

            stock_previo = producto.cantidad
            producto.cantidad -= cantidad_vender

            nueva_transaccion = Transacciones(
                producto_id=producto.id,
                cantidad=cantidad_vender,
                fecha=datetime.utcnow(),
                tipo="Venta",
                stock_anterior=stock_previo,
                referencia=codigo_recibo,
                precio_unitario=item.get('precio', producto.precio),
                costo_unitario=item.get('costo', producto.costo)
            )
            db.session.add(nueva_transaccion)

    # 4. Generar automáticamente las órdenes de Dropshipping divididas por proveedor
    if dropshipping_por_proveedor and cliente_obj:
        db.session.flush()
        counter = 1
        for prov_id, items_ds in dropshipping_por_proveedor.items():
            ref_drop = f"DROP-{codigo_recibo.replace('VTA-', '')}-{counter}"
            counter += 1

            costo_tot = sum(i['costo'] * i['cantidad'] for i in items_ds)
            venta_tot = sum(i['precio'] * i['cantidad'] for i in items_ds)
            ganancia_tot = venta_tot - costo_tot

            nueva_orden_ds = OrdenDropshipping(
                referencia=ref_drop,
                cliente_id=cliente_obj.id,
                proveedor_id=prov_id,
                fecha_creacion=datetime.utcnow(),
                estado='Procesando',
                costo_total=costo_tot,
                venta_total=venta_tot,
                ganancia=ganancia_tot,
                pago_cliente_estado='Pagado' if estado_pago == 'Pagada' else estado_pago,
                pago_cliente_monto=venta_tot if estado_pago == 'Pagada' else 0
            )
            db.session.add(nueva_orden_ds)
            db.session.flush()

            for i in items_ds:
                det_ds = DetalleDropshipping(
                    orden_id=nueva_orden_ds.id,
                    producto_id=i['producto'].id,
                    cantidad=i['cantidad'],
                    costo_unitario=i['costo'],
                    precio_venta_unitario=i['precio']
                )
                db.session.add(det_ds)

    db.session.commit()
    return codigo_recibo


def generar_recibo_excel(guia, transacciones, es_devolucion=False, es_ajuste=False, vendedor_telefono='', vendedor_display='', formato='con-encabezado'):
    """
    Genera un archivo Excel (.xlsx) paginado idéntico al recibo / guía de despacho web
    y a las formas continuas de imprenta (16 productos por hoja, encabezado de cliente,
    despachamos en gris, columnas de items, firmas y totales por página).
    Si tiene varias páginas, genera una hoja 'Recibo Completo' con saltos de página para
    impresión continua, y pestañas individuales ('Pág. 1', 'Pág. 2', etc.).
    """
    import io
    import math
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.worksheet.pagebreak import Break

    # 8.25pt = los 11px que usa recibo.css para la tabla y el bloque de datos
    # del cliente, asi el Excel imprime con el mismo tamano de letra que el
    # recibo HTML/PDF.
    font_arial = Font(name='Arial', size=8.25)
    font_bold = Font(name='Arial', size=8.25, bold=True)
    font_lbl = Font(name='Arial', size=8.25, bold=True)
    fill_gray = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')

    # ====================== NO TOCAR SIN IMPRIMIR ======================
    # Suman 84 unidades. Es el UNICO valor verificado contra la impresora real.
    # Historial de intentos de ensanchar la columna C (descripcion):
    #   C=38 (84 u total)  -> imprime bien
    #   C=48 (94 u total)  -> WPS partio las columnas: la hoja de 1 pagina paso
    #                         a "1 de 2" mostrando solo Cantidad y Codigo
    #   C=56 (99 u total)  -> igual, 9 paginas en vez de 3
    # El calculo de unidades a centimetros NO sirve para predecirlo, y comparar
    # unidades contra el .xls del dueno tampoco: el formato BIFF viejo guarda
    # el ancho en 1/256 de caracter de SU fuente por defecto, que no es la
    # misma que la de este libro, asi que los numeros no son equivalentes.
    # Consecuencia: la descripcion no puede mostrar tanto texto como el recibo
    # web. Se recorta con "..." (ver MAX_DESC mas abajo).
    # ===================================================================
    col_widths = {'A': 8, 'B': 14, 'C': 38, 'D': 12, 'E': 12}

    def aplicar_setup_pagina(ws):
        # Vista de salto de pagina (Page Break Preview):
        # Muestra la hoja delimitada en blanco y todo lo que este fuera (a partir de la columna F)
        # en fondo gris oscuro continuo, bloqueando visualmente las columnas extras.
        ws.sheet_view.view = 'pageBreakPreview'

        # Sin cuadricula: el recibo HTML/PDF no la tiene, y al abrir el .xlsx
        # la reja gris de Excel es lo que mas lo hace ver distinto al PDF.
        # Solo afecta la vista en pantalla; al imprimir nunca salia (eso lo
        # controla print_options.gridLines, que va en False por defecto).
        ws.views.sheetView[0].showGridLines = False
        for col_letter, width in col_widths.items():
            ws.column_dimensions[col_letter].width = width

        # El recibo solo usa A:E. Se ocultan las columnas de la F en adelante
        # para que la hoja "termine" ahi y todo lo que sigue se vea en gris,
        # como una hoja cerrada, en vez de una cuadricula infinita vacia.
        # No afecta la impresion (esas columnas van vacias de todos modos).
        ws.column_dimensions.group('F', 'XFD', hidden=True)
        # group() ademas marca un nivel de esquema, y eso hace que Excel pinte
        # arriba la barrita de agrupar/desagrupar con el boton "+". Solo
        # queremos ocultarlas, no agruparlas.
        ws.column_dimensions['F'].outlineLevel = 0

        ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
        ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
        ws.print_options.horizontalCentered = True
        ws.sheet_properties.pageSetUpPr.fitToPage = False
        ws.page_setup.scale = 100

        # Mismos márgenes que recibo.html y recibo_encabezado.html (data-margen-*)
        # en los dos formatos, así el Excel no imprime descuadrado respecto a
        # la impresión directa del navegador.
        ws.page_margins.top = 4.3 / 2.54         # 4.3 cm de margen superior
        ws.page_margins.bottom = 2.0 / 2.54      # 2.0 cm de margen inferior
        ws.page_margins.left = 1.0 / 2.54        # 1.0 cm de margen lateral
        ws.page_margins.right = 1.0 / 2.54
        
    # El bloque de productos se rellena con filas en blanco hasta este numero
    # para que el pie de firmas y totales caiga SIEMPRE en la misma fila, tenga
    # la venta 1 producto o el maximo. Calibrado para los margenes actuales
    # (top 4.3 / bottom 2.0 -> 21.64cm utiles) con filas de producto de 15pt:
    # 26 filas dejan ~0.8cm de colchon. Si se cambian margenes o alturas de
    # fila, hay que recalcular este numero o reaparece el hueco en blanco.
    # DEBE ser igual al numero de productos que el paginador del recibo web
    # (recibo_paginador.js) mete por hoja, hoy 25. Los totales son POR PAGINA,
    # asi que si el Excel pone 26 y el HTML 25, la Base Imponible y el TOTAL de
    # cada hoja no cuadran entre las dos salidas aunque la venta sea la misma.
    # Si se cambian margenes, padding de .table-custom td o alturas de fila,
    # hay que volver a contar cuantas filas entran en el recibo web y ajustar
    # este numero a ese valor.
    ITEMS_POR_PAGINA = 25
    ALTO_FILA_PRODUCTO = 15
    total_items = len(transacciones)
    total_paginas = max(1, math.ceil(total_items / ITEMS_POR_PAGINA))

    total_bruto_venta = sum(
        float(t.cantidad) * (float(t.precio_unitario) if t.precio_unitario is not None else float(t.producto.precio or 0.0))
        for t in transacciones
    ) if not es_ajuste else 0.0
    descuento_global = round(float(guia.descuento_global or 0.0), 2) if not es_ajuste else 0.0

    def render_bloque_hoja(ws, start_row, page_items, p_idx, desc_acumulado_estado):
        r = start_row
        es_ultima = (p_idx == total_paginas - 1)

        # 1. Encabezado de Cliente
        # Fila 1: Nombre / Razón Social y Fecha
        ws.row_dimensions[r].height = 20
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        lbl_pag = ""
        c = ws.cell(row=r, column=1, value=f'Nombre y Apellido ó Razón Social{lbl_pag}')
        c.font = font_lbl
        c.alignment = Alignment(vertical='center')

        c = ws.cell(row=r, column=3, value=(guia.cliente_nombre or 'N/A').upper())
        c.font = font_arial
        c.alignment = Alignment(vertical='center')

        c = ws.cell(row=r, column=4, value='Fecha:')
        c.font = font_lbl
        c.alignment = Alignment(horizontal='right', vertical='center')

        c = ws.cell(row=r, column=5, value=guia.fecha.strftime('%d/%m/%Y') if guia.fecha else '')
        c.font = font_arial
        c.alignment = Alignment(horizontal='right', vertical='center')

        # Fila 2: Domicilio Fiscal y RIF
        ws.row_dimensions[r+1].height = 20
        ws.merge_cells(start_row=r+1, start_column=1, end_row=r+1, end_column=2)
        c = ws.cell(row=r+1, column=1, value='Domicilio Fiscal (Domicilio)')
        c.font = font_lbl
        c.alignment = Alignment(vertical='center')

        c = ws.cell(row=r+1, column=3, value=(guia.cliente_direccion or 'N/A').upper())
        c.font = font_arial
        c.alignment = Alignment(vertical='center')

        c = ws.cell(row=r+1, column=4, value='RIF.')
        c.font = font_lbl
        c.alignment = Alignment(horizontal='right', vertical='center')

        c = ws.cell(row=r+1, column=5, value=guia.cliente_identificacion or 'N/A')
        c.font = font_arial
        c.alignment = Alignment(horizontal='right', vertical='center')

        # Fila 3: Ciudad y Teléfono
        ws.row_dimensions[r+2].height = 18
        ws.merge_cells(start_row=r+2, start_column=1, end_row=r+2, end_column=2)
        c = ws.cell(row=r+2, column=1, value=f"Ciudad: {(guia.ciudad or 'N/A').upper()}")
        c.font = font_lbl
        c.alignment = Alignment(vertical='center')

        c = ws.cell(row=r+2, column=3, value=f"Teléfono: {guia.cliente_telefono or 'N/A'}")
        c.font = font_lbl
        c.alignment = Alignment(vertical='center')

        # Caja gris: Despachamos a Ud. (s) lo siguiente (abarca D y E)
        ws.merge_cells(start_row=r+2, start_column=4, end_row=r+3, end_column=5)
        box = ws.cell(row=r+2, column=4, value='Despachamos a Ud. (s) lo siguiente:')
        box.font = font_lbl
        box.fill = fill_gray
        box.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        # Fila 4: Vendedor y Teléfono Vendedor
        ws.row_dimensions[r+3].height = 18
        ws.merge_cells(start_row=r+3, start_column=1, end_row=r+3, end_column=2)
        v_nom = (vendedor_display or guia.vendedor_nombre or 'N/A').title()
        c = ws.cell(row=r+3, column=1, value=f"Vendedor(a): {v_nom}")
        c.font = font_lbl
        c.alignment = Alignment(vertical='center')

        c = ws.cell(row=r+3, column=3, value=f"Tlf: {vendedor_telefono or ''}")
        c.font = font_lbl
        c.alignment = Alignment(vertical='center')

        # Fila 5: Espacio separador
        ws.row_dimensions[r+4].height = 10

        # Fila 6: Encabezados de la Tabla de Productos (fondo #ccc)
        ws.row_dimensions[r+5].height = 20
        if es_ajuste:
            headers = ['Cantidad', 'Código', 'Descripción del artículo', 'Stock Ant.', 'Tipo']
        else:
            headers = ['Cantidad', 'Código', 'Descripción del artículo', 'Precio Unit.', 'Precio Total']

        for col_idx, h in enumerate(headers, 1):
            c = ws.cell(row=r+5, column=col_idx, value=h)
            c.font = font_bold
            c.fill = fill_gray
            c.alignment = Alignment(horizontal='right' if col_idx in [4, 5] and not es_ajuste else 'left')

        # 2. Filas de Productos
        prod_row = r + 6
        monto_bruto_pagina = 0.0
        for t in page_items:
            ws.row_dimensions[prod_row].height = ALTO_FILA_PRODUCTO

            c1 = ws.cell(row=prod_row, column=1, value=t.cantidad)
            c1.alignment = Alignment(horizontal='left')
            c1.font = font_arial

            cod = t.producto.descripcion.replace('CÓDIGO: ', '').strip() if t.producto and t.producto.descripcion else ''
            c2 = ws.cell(row=prod_row, column=2, value=cod)
            c2.alignment = Alignment(horizontal='left')
            c2.font = font_arial

            nombre = (t.producto.nombre if t.producto else 'Desconocido').upper()
            sufijo = ' *' if (getattr(t, 'tipo', '') == 'Venta (Dropshipping)' or (t.producto and getattr(t.producto, 'es_dropshipping', False))) else ''
            # Recorta con puntos suspensivos igual que el CSS del recibo web
            # (text-overflow: ellipsis en .table-custom td). Sin esto, Excel no
            # envuelve el texto y corta la descripcion a mitad de palabra en el
            # borde de la columna, sin ningun aviso visual. El limite es el
            # limite lo marca el ancho de col_widths['C'] (38 unidades con
            # Arial 8.25 da para ~46 caracteres). El recibo web recorta mas
            # tarde (~60) porque alli la columna es mas ancha; aqui no se puede
            # igualar sin que Excel parta las columnas de pagina.
            MAX_DESC = 46
            espacio = MAX_DESC - len(sufijo)
            if len(nombre) > espacio:
                nombre = nombre[:espacio - 1].rstrip() + '…'
            nombre += sufijo
            c3 = ws.cell(row=prod_row, column=3, value=nombre)
            c3.alignment = Alignment(horizontal='left')
            c3.font = font_arial

            if es_ajuste:
                c4 = ws.cell(row=prod_row, column=4, value=t.stock_anterior if t.stock_anterior is not None else 'N/A')
                c4.alignment = Alignment(horizontal='center')
                c4.font = font_arial

                c5 = ws.cell(row=prod_row, column=5, value=t.tipo or 'Ajuste')
                c5.alignment = Alignment(horizontal='center')
                c5.font = font_arial
            else:
                if t.precio_unitario is not None:
                    pu = float(t.precio_unitario)
                elif t.producto and t.producto.precio is not None:
                    pu = float(t.producto.precio)
                else:
                    pu = 0.0

                c4 = ws.cell(row=prod_row, column=4, value=round(pu, 2))
                c4.number_format = '#,##0.00'
                c4.alignment = Alignment(horizontal='right')
                c4.font = font_arial

                pt = round(float(t.cantidad) * pu, 2)
                monto_bruto_pagina += pt
                c5 = ws.cell(row=prod_row, column=5, value=pt)
                c5.number_format = '#,##0.00'
                c5.alignment = Alignment(horizontal='right')
                c5.font = font_arial

            prod_row += 1

        monto_bruto_pagina = round(monto_bruto_pagina, 2)

        # Rellenar filas vacías hasta ITEMS_POR_PAGINA para anclar el pie exactamente en su posición
        filas_faltantes = ITEMS_POR_PAGINA - len(page_items)
        for _ in range(filas_faltantes):
            ws.row_dimensions[prod_row].height = ALTO_FILA_PRODUCTO
            prod_row += 1

        # Espacio antes del pie
        ws.row_dimensions[prod_row].height = 20
        prod_row += 1

        pie_start = prod_row

        # 3. Pie de página: Firmas y Observaciones
        ws.cell(row=pie_start, column=1, value='Despachado por:').font = font_bold
        ws.cell(row=pie_start, column=2, value='___________________________').font = font_arial
        ws.cell(row=pie_start, column=3, value='Fecha de entrega:  _______________________').font = font_bold

        ws.cell(row=pie_start + 1, column=1, value='Recibido por:').font = font_bold
        ws.cell(row=pie_start + 1, column=2, value='___________________________').font = font_arial
        obs_txt = f"Observaciones:       {guia.observaciones}" if guia.observaciones else 'Observaciones:       _______________________'
        ws.cell(row=pie_start + 1, column=3, value=obs_txt).font = font_bold

        ws.merge_cells(start_row=pie_start + 3, start_column=1, end_row=pie_start + 3, end_column=2)
        c_thx = ws.cell(row=pie_start + 3, column=1, value='Gracias por su confianza')
        c_thx.font = font_bold

        # 4. Totales correspondientes a los productos de esta página (idéntico a recibo_paginador.js)
        if es_ajuste:
            c_lbl = ws.cell(row=pie_start, column=4, value='Tipo:')
            c_lbl.font = font_bold
            c_val = ws.cell(row=pie_start, column=5, value='Ajuste Manual')
            c_val.font = font_arial
            c_val.alignment = Alignment(horizontal='right')

            c_lbl2 = ws.cell(row=pie_start + 1, column=4, value='Productos:')
            c_lbl2.font = font_bold
            c_val2 = ws.cell(row=pie_start + 1, column=5, value=len(page_items))
            c_val2.font = font_arial
            c_val2.alignment = Alignment(horizontal='right')

            next_row = pie_start + 5
        else:
            if descuento_global > 0 and total_bruto_venta > 0:
                if es_ultima:
                    desc_pagina = round(descuento_global - desc_acumulado_estado[0], 2)
                else:
                    desc_pagina = round(descuento_global * (monto_bruto_pagina / total_bruto_venta), 2)
                    desc_acumulado_estado[0] = round(desc_acumulado_estado[0] + desc_pagina, 2)
            else:
                desc_pagina = 0.0

            base_imponible = round(monto_bruto_pagina - desc_pagina, 2)
            igtf = round(base_imponible * 0.03, 2)
            iva = round(base_imponible * 0.16, 2)
            subtotal = round(base_imponible + igtf, 2)
            total_pagina = round(subtotal + iva, 2)

            curr_tot_row = pie_start
            if desc_pagina > 0:
                c = ws.cell(row=curr_tot_row, column=4, value='Monto Bruto')
                c.font = font_arial
                c = ws.cell(row=curr_tot_row, column=5, value=monto_bruto_pagina)
                c.font = font_arial
                c.number_format = '#,##0.00'
                c.alignment = Alignment(horizontal='right')
                curr_tot_row += 1

                c = ws.cell(row=curr_tot_row, column=4, value='Desc. Global')
                c.font = font_arial
                c = ws.cell(row=curr_tot_row, column=5, value=-desc_pagina)
                c.font = font_arial
                c.number_format = '#,##0.00'
                c.alignment = Alignment(horizontal='right')
                curr_tot_row += 1

            c = ws.cell(row=curr_tot_row, column=4, value='Base Imponible')
            c.font = font_arial
            c = ws.cell(row=curr_tot_row, column=5, value=base_imponible)
            c.font = font_arial
            c.number_format = '#,##0.00'
            c.alignment = Alignment(horizontal='right')
            curr_tot_row += 1

            c = ws.cell(row=curr_tot_row, column=4, value='IGTF 3%')
            c.font = font_arial
            c = ws.cell(row=curr_tot_row, column=5, value=igtf)
            c.font = font_arial
            c.number_format = '#,##0.00'
            c.alignment = Alignment(horizontal='right')
            curr_tot_row += 1

            c = ws.cell(row=curr_tot_row, column=4, value='Sub-Total')
            c.font = font_arial
            c = ws.cell(row=curr_tot_row, column=5, value=subtotal)
            c.font = font_arial
            c.number_format = '#,##0.00'
            c.alignment = Alignment(horizontal='right')
            curr_tot_row += 1

            c = ws.cell(row=curr_tot_row, column=4, value='IVA (16%)')
            c.font = font_arial
            c = ws.cell(row=curr_tot_row, column=5, value=iva)
            c.font = font_arial
            c.number_format = '#,##0.00'
            c.alignment = Alignment(horizontal='right')
            curr_tot_row += 1

            c_lbl = ws.cell(row=curr_tot_row, column=4, value='TOTAL')
            c_lbl.font = font_bold
            c_lbl.fill = fill_gray

            c_val = ws.cell(row=curr_tot_row, column=5, value=total_pagina)
            c_val.font = font_bold
            c_val.fill = fill_gray
            c_val.number_format = '#,##0.00'
            c_val.alignment = Alignment(horizontal='right')

            next_row = curr_tot_row + 1

        return next_row

    wb = openpyxl.Workbook()

    if total_paginas == 1:
        ws = wb.active
        ws.title = "Recibo"
        aplicar_setup_pagina(ws)
        end_r = render_bloque_hoja(ws, start_row=1, page_items=transacciones, p_idx=0, desc_acumulado_estado=[0.0])
        ws.print_area = f"A1:E{end_r - 1}"
    else:
        # 1. Hoja "Recibo Completo" con todas las páginas y saltos de página para impresión continua
        ws_completo = wb.active
        ws_completo.title = "Recibo Completo"
        aplicar_setup_pagina(ws_completo)

        desc_acum = [0.0]
        current_r = 1
        for p in range(total_paginas):
            p_items = transacciones[p * ITEMS_POR_PAGINA : (p + 1) * ITEMS_POR_PAGINA]
            end_r = render_bloque_hoja(ws_completo, current_r, p_items, p, desc_acum)
            if p < total_paginas - 1:
                ws_completo.row_breaks.append(Break(id=end_r - 1))
                ws_completo.row_dimensions[end_r].height = 10
                current_r = end_r + 1
        ws_completo.print_area = f"A1:E{current_r - 1}"

        # 2. Pestañas individuales para cada página ("Pág. 1", "Pág. 2", etc.)
        desc_acum_tabs = [0.0]
        for p in range(total_paginas):
            ws_p = wb.create_sheet(title=f"Pág. {p+1}")
            aplicar_setup_pagina(ws_p)
            p_items = transacciones[p * ITEMS_POR_PAGINA : (p + 1) * ITEMS_POR_PAGINA]
            end_r_p = render_bloque_hoja(ws_p, start_row=1, page_items=p_items, p_idx=p, desc_acumulado_estado=desc_acum_tabs)
            ws_p.print_area = f"A1:E{end_r_p - 1}"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


