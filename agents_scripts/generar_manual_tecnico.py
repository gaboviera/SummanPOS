"""Genera el Manual Técnico de SummanPOS (.docx) con portada institucional.

Entradas: metadatos.json (extraer_metadatos_tecnicos.py), PNG de diagramas
(generar_diagramas_tecnicos.py + Playwright) y la portada .docx.

Uso:
    python agents_scripts/generar_manual_tecnico.py \
        --metadatos .tmp/manual_tecnico/metadatos.json \
        --diagramas .tmp/manual_tecnico \
        --portada "C:/ruta/PortadaIujo.docx" \
        --salida docs/manual_tecnico/Manual_Tecnico_SummanPOS.docx
"""
import argparse
import ast
import json
import os
import sys
from datetime import date

import docx
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

sys.path.insert(0, os.path.dirname(__file__))
from actualizar_manual_docx import insertar_portada  # noqa: E402

RAIZ_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP = os.path.join(RAIZ_REPO, "flask_iventario")
MORADO = RGBColor(0x4B, 0x2C, 0x7F)
OSCURO = RGBColor(0x26, 0x16, 0x40)

# ----------------------------------------------------------------- textos
DESC_TABLAS = {
    "roles": "Catálogo de roles de acceso (Super Admin, Administrador, Supervisor, Cajero).",
    "usuarios": "Cuentas de acceso al sistema con contraseña cifrada (Bcrypt) y rol asignado.",
    "atributos": "Atributos dinámicos de productos (Marca, Color, Tamaño) al estilo Odoo.",
    "valores_atributos": "Valores posibles de cada atributo (p. ej. TOYOTA, FORD para Marca).",
    "productos_valores": "Tabla puente N:M entre productos y valores de atributos.",
    "categorias": "Familias o categorías de inventario.",
    "productos": "Catálogo maestro de repuestos/artículos con stock, precio y costo.",
    "tasa_cambio": "Histórico de cotizaciones (BCV USD, BCV EURO, USDT Binance, manual).",
    "inventario": "Registro histórico de existencias por fecha (tabla heredada).",
    "transacciones": "Kardex: cada entrada/salida de stock con stock anterior y precios.",
    "proveedores": "Proveedores heredados (antes de unificarse en contactos).",
    "productos_proveedores": "Tabla puente N:M heredada entre productos y proveedores.",
    "contactos": "Directorio unificado de clientes y proveedores con tarifa preferida.",
    "guias_despacho": "Ventas / guías de despacho (notas de entrega) con totales y tasas del día.",
    "ordenes_compra": "Órdenes de compra a proveedores y su estado de recepción y pago.",
    "detalle_orden_compra": "Líneas de cada orden de compra (cantidad pedida/recibida y costo).",
    "configuracion": "Parámetros clave-valor del sistema (logo, favicon, módulos activos).",
    "notificaciones": "Alertas del sistema por usuario (o globales) y su estado de lectura.",
    "listas_precios": "Reglas de listas de precios (BCV, USDT, Euro, Mayorista) sobre el precio base.",
    "producto_precios": "Precio excepcional de un producto en una lista concreta.",
    "ordenes_dropshipping": "Pedidos por encargo despachados por un proveedor aliado.",
    "detalle_dropshipping": "Líneas de cada orden de dropshipping con costo y precio de venta.",
    "pagos_cxc": "Abonos de clientes a ventas a crédito (Cuentas por Cobrar).",
    "pagos_cxp": "Pagos a proveedores por órdenes de compra (Cuentas por Pagar).",
    "pagos_dropshipping": "Pagos asociados a órdenes de dropshipping.",
}
DESC_COLS = {
    "id": "Identificador único autoincremental.",
    "nombre": "Nombre descriptivo del registro.",
    "deleted_at": "Fecha de baja lógica (soft delete); NULL si está activo.",
    "fecha": "Fecha y hora del registro.",
    "referencia": "Código de referencia legible (p. ej. VTA-..., OC-..., DROP-...).",
    "estado": "Estado del documento en su ciclo de vida.",
    "estado_pago": "Estado de pago: Pagado, Pendiente o Parcial.",
    "monto_abonado": "Suma de abonos registrados hasta la fecha (USD).",
    "fecha_vencimiento": "Fecha límite de pago para crédito.",
    "observaciones": "Notas libres del operador.",
    "total": "Monto total del documento en USD.",
    "monto": "Monto del pago en USD.",
    "metodo": "Método de pago (Pago Móvil, Zelle, Efectivo, etc.).",
    "referencia_pago": "Número de comprobante bancario o referencia.",
    "tasa_usada": "Tasa de cambio aplicada al pago.",
    "moneda_tasa": "Moneda de la tasa (BCV, USDT, EUR).",
    "monto_moneda": "Monto equivalente en la moneda local pagada.",
    "producto_id": "Producto relacionado.",
    "orden_id": "Orden a la que pertenece el registro.",
    "proveedor_id": "Contacto proveedor relacionado.",
    "cantidad": "Cantidad de unidades.",
    "costo_unitario": "Costo por unidad en USD.",
    "precio_unitario": "Precio de venta por unidad en USD.",
    "tipo": "Clasificación del registro.",
    "valor": "Valor asociado.",
}
DESC_ESPECIFICAS = {
    ("usuarios", "username"): "Nombre de usuario o correo para iniciar sesión.",
    ("usuarios", "password_hash"): "Hash Bcrypt de la contraseña (nunca texto plano).",
    ("usuarios", "rol_id"): "Rol de acceso del usuario.",
    ("usuarios", "activo"): "Indica si la cuenta puede iniciar sesión.",
    ("productos", "descripcion"): "Descripción técnica del artículo.",
    ("productos", "categoria_id"): "Categoría a la que pertenece.",
    ("productos", "cantidad"): "Existencia física actual.",
    ("productos", "precio"): "Precio base de venta en USD.",
    ("productos", "costo"): "Costo de adquisición en USD.",
    ("productos", "es_dropshipping"): "Indica si se vende por encargo sin stock propio.",
    ("tasa_cambio", "tasa"): "Valor de la cotización en Bs.",
    ("tasa_cambio", "fuente"): "Origen: BCV, BCV_EURO, USDT o MANUAL.",
    ("transacciones", "tipo"): "Tipo de movimiento (Entrada, Salida, Venta, Ajuste...).",
    ("transacciones", "stock_anterior"): "Existencia antes del movimiento.",
    ("contactos", "identificacion"): "RIF o cédula del contacto.",
    ("contactos", "correo"): "Correo electrónico.",
    ("contactos", "direccion"): "Dirección fiscal.",
    ("contactos", "ciudad"): "Ciudad.",
    ("contactos", "telefono"): "Teléfono (usado para cobro por WhatsApp).",
    ("contactos", "tipo"): "Cliente, Proveedor, Ambos o Contacto Usuario.",
    ("contactos", "lista_precio_id"): "Tarifa predeterminada aplicada en el POS.",
    ("guias_despacho", "vendedor_id"): "Usuario que registró la venta.",
    ("guias_despacho", "descuento_global"): "Descuento aplicado a toda la venta.",
    ("guias_despacho", "tasa_bcv"): "Tasa BCV del momento de la venta.",
    ("guias_despacho", "tasa_euro"): "Tasa Euro BCV del momento de la venta.",
    ("guias_despacho", "tasa_usdt"): "Tasa USDT del momento de la venta.",
    ("ordenes_compra", "fecha_creacion"): "Fecha de emisión de la orden.",
    ("ordenes_compra", "fecha_recepcion"): "Fecha de recepción en almacén.",
    ("detalle_orden_compra", "cantidad_pedida"): "Unidades solicitadas.",
    ("detalle_orden_compra", "cantidad_recibida"): "Unidades recibidas (recepción parcial).",
    ("detalle_orden_compra", "subtotal"): "Cantidad x costo unitario.",
    ("configuracion", "clave"): "Nombre del parámetro (p. ej. logo_url).",
    ("configuracion", "valor"): "Valor del parámetro.",
    ("notificaciones", "usuario_id"): "Destinatario; NULL = notificación global.",
    ("notificaciones", "mensaje"): "Texto de la alerta.",
    ("notificaciones", "leida"): "Indica si el usuario ya la leyó.",
    ("listas_precios", "basado_en"): "Precio de referencia (Precio Base, Costo).",
    ("listas_precios", "operador"): "Operación aplicada (aumento / descuento).",
    ("listas_precios", "valor_regla"): "Porcentaje o monto de la regla.",
    ("listas_precios", "moneda"): "Moneda de la lista (USD, BCV, USDT, EUR).",
    ("listas_precios", "activa"): "Indica si la lista está disponible en ventas.",
    ("producto_precios", "lista_id"): "Lista de precios del precio excepcional.",
    ("producto_precios", "precio"): "Precio fijo del producto en esa lista.",
    ("ordenes_dropshipping", "cliente_id"): "Cliente final del pedido.",
    ("ordenes_dropshipping", "empresa_transporte"): "Courier encargado del envío.",
    ("ordenes_dropshipping", "numero_seguimiento"): "Número de guía / tracking.",
    ("ordenes_dropshipping", "costo_total"): "Costo total pagado al proveedor.",
    ("ordenes_dropshipping", "venta_total"): "Total cobrado al cliente.",
    ("ordenes_dropshipping", "ganancia"): "Venta total menos costo total.",
    ("detalle_dropshipping", "precio_venta_unitario"): "Precio de venta por unidad.",
    ("pagos_cxc", "guia_id"): "Venta (guía de despacho) abonada.",
    ("inventario", "fecha"): "Fecha del registro de existencia.",
    ("valores_atributos", "atributo_id"): "Atributo al que pertenece el valor.",
    ("productos_valores", "valor_id"): "Valor de atributo asignado al producto.",
}
DESC_MODULOS = {
    "app.py": "Punto de entrada. create_app() configura Flask, la conexión PostgreSQL, extensiones, "
              "registra los 13 blueprints, programa tareas APScheduler e inyecta variables globales a "
              "las plantillas. Define el comando CLI 'flask seed-inicial'.",
    "extensions.py": "Instancias compartidas de SQLAlchemy, Migrate, Bcrypt y LoginManager.",
    "models.py": "Modelos ORM (25 tablas) y el user_loader de Flask-Login.",
    "forms.py": "Formularios Flask-WTF (LoginForm y otros) con validación y token CSRF.",
    "utils/decorators.py": "Decorador @rol_requerido(*roles): control de acceso por rol; Super Admin pasa siempre.",
    "routes/auth_routes.py": "Landing, inicio y cierre de sesión.",
    "routes/inventario_routes.py": "Dashboard, CRUD de productos, papelera, lista de precios, exportación "
                                   "PDF/Excel, kardex, carga masiva desde Excel y descargas.",
    "routes/ventas_routes.py": "Punto de venta, procesamiento de ventas, recibos, historial y anulación.",
    "routes/compras_routes.py": "Órdenes de compra, recepción de mercancía y comprobantes.",
    "routes/finanzas_routes.py": "Cuentas por cobrar/pagar, abonos y flujo de pagos.",
    "routes/contactos_routes.py": "Directorio de clientes y proveedores, API de contactos, exportaciones.",
    "routes/categorias_routes.py": "CRUD de categorías.",
    "routes/atributos_routes.py": "CRUD de atributos y API JSON de valores.",
    "routes/usuarios_routes.py": "Gestión de usuarios y roles (solo administradores).",
    "routes/bcv_routes.py": "Historial y actualización de tasas BCV/Euro/USDT, fijación manual.",
    "routes/configuracion_routes.py": "Identidad corporativa, listas de precios y módulos opcionales.",
    "routes/notificaciones_routes.py": "Historial y marcado de notificaciones.",
    "routes/dropshipping_routes.py": "Módulo opcional de pedidos por encargo (se bloquea si está desactivado).",
    "services/": "Capa de lógica de negocio: cada *_service.py encapsula consultas y reglas "
                 "(cálculo de IVA/IGTF, stock, abonos, scraping de tasas) para mantener delgados los controladores.",
}
ROLES = [
    ("Super Admin", "Acceso total. El decorador @rol_requerido lo deja pasar en cualquier vista. "
                    "Se asigna automáticamente al usuario 'admin' en la siembra inicial."),
    ("Administrador", "Gestión de usuarios, configuración del sistema, eliminación (soft delete), "
                      "papelera, ajustes de stock y métricas financieras completas."),
    ("Supervisor", "Gestión operativa: productos (crear/editar), compras, categorías y atributos, "
                   "ventas y contactos. Sin acceso a usuarios, configuración ni borrados."),
    ("Cajero", "Punto de venta, recibos, consulta de catálogo y registro de clientes."),
]
ERRORES = [
    ("Las tablas no existen todavía (aviso al arrancar)",
     "No se aplicaron las migraciones.", "Ejecutar 'flask db upgrade' y luego 'flask seed-inicial'."),
    ("Can't locate revision ... (Alembic)",
     "La base apunta a una revisión que ya no existe en migrations/versions.",
     "En el despliegue se corrige con 'flask db stamp --purge head'; en local, revisar 'flask db current'."),
    ("'flask db check' falla tras migrar",
     "El esquema real no coincide con models.py.",
     "Generar la migración faltante con 'flask db migrate -m ...' y aplicarla."),
    ("psycopg2.OperationalError: connection refused",
     "PostgreSQL apagado o variables PGHOST/PGPORT/PGUSER incorrectas.",
     "Verificar el servicio de BD y el archivo .env; probar con 'psql'."),
    ("Error al generar PDF (WeasyPrint: cannot load library pango)",
     "Faltan librerías del sistema de WeasyPrint (común en Windows).",
     "Usar el contenedor Docker o instalar GTK/Pango; en Debian: libpango-1.0-0 libpangoft2-1.0-0."),
    ("Las tasas BCV/USDT no se actualizan",
     "Cambio en la página del BCV o sin salida a internet.",
     "Usar 'Fijar Tasa Manual' en /bcv/historial y revisar los logs del scheduler."),
    ("502 Bad Gateway en el dominio",
     "El contenedor no está arriba o Caddy apunta a otro nombre de contenedor.",
     "'docker-compose ps', revisar logs y el Caddyfile del entorno."),
    ("Error 500 al entrar a /dropshipping con el módulo desactivado",
     "El before_request redirige a 'inventario.index', endpoint que no existe (BuildError).",
     "Activar el módulo en Configuración → Módulos y Funciones o corregir la redirección a 'inventario.dashboard'."),
    ("Log de Gunicorn: 'Control server error: Permission denied: /home/appuser'",
     "El usuario no-root del contenedor no tiene carpeta personal; no afecta el servicio.",
     "Ignorar, o crear el usuario con home (useradd -m) en el Dockerfile."),
    ("Las sesiones se cierran tras un despliegue / advertencia de seguridad",
     "SECRET_KEY no está definida y se usa el valor por defecto.",
     "Definir SECRET_KEY única y secreta en el .env del entorno."),
]


# ----------------------------------------------------------------- helpers
def sombrear(celda, color):
    tcpr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcpr.append(shd)


def tabla(doc, encabezados, filas, anchos=None, tam=9):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(encabezados):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(tam)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        sombrear(c, "4B2C7F")
    # repetir encabezado en cada página
    trpr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trpr.append(th)
    for n, fila in enumerate(filas):
        cells = t.add_row().cells
        for i, v in enumerate(fila):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(tam)
            if n % 2:
                sombrear(cells[i], "F3EEFA")
    if anchos:
        for row in t.rows:
            for i, w in enumerate(anchos):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t


def codigo(doc, texto):
    for linea in texto.strip("\n").split("\n"):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(0.5)
        r = p.add_run(linea if linea else " ")
        r.font.name = "Consolas"
        r.font.size = Pt(9)
        ppr = p._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), "F2F2F2")
        ppr.append(shd)
    doc.add_paragraph()


def vinetas(doc, items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        if isinstance(it, tuple):
            p.add_run(it[0] + ": ").bold = True
            p.add_run(it[1])
        else:
            p.add_run(it)


def figura(doc, ruta, pie, ancho_cm):
    doc.add_picture(ruta, width=Cm(ancho_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph(pie)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].italic = True
    p.runs[0].font.size = Pt(9)


def salto(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def toc(doc):
    p = doc.add_paragraph()
    r = p.add_run()
    for tag, txt in (("begin", None), (None, 'TOC \\o "1-2" \\h \\z \\u'), ("separate", None)):
        if tag:
            f = OxmlElement("w:fldChar")
            f.set(qn("w:fldCharType"), tag)
            r._r.append(f)
        else:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = txt
            r._r.append(it)
    r2 = p.add_run("Actualice el índice (clic derecho → Actualizar campos).")
    f = OxmlElement("w:fldChar")
    f.set(qn("w:fldCharType"), "end")
    r2._r.append(f)


def nueva_seccion(doc, horizontal):
    s = doc.add_section()
    if horizontal:
        s.orientation = WD_ORIENT.LANDSCAPE
        s.page_width, s.page_height = Cm(29.7), Cm(21)
    else:
        s.orientation = WD_ORIENT.PORTRAIT
        s.page_width, s.page_height = Cm(21), Cm(29.7)
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(s, m, Cm(2))
    return s


def arbol(base, prefijo="", nivel=0, max_nivel=2):
    excluir = {"__pycache__", ".git", "uploads", "db_dumps", "data", "_archive_pre_baseline",
               ".venv", "venv", "node_modules"}
    lineas = []
    items = sorted(e for e in os.listdir(base) if e not in excluir and not e.endswith((".pyc", ".lock")))
    items = [e for e in items if not e.endswith(".metadata.json")]
    for i, e in enumerate(items):
        ruta = os.path.join(base, e)
        ult = i == len(items) - 1
        lineas.append(f"{prefijo}{'└── ' if ult else '├── '}{e}{'/' if os.path.isdir(ruta) else ''}")
        if os.path.isdir(ruta) and nivel < max_nivel:
            if e == "versions":
                n = len([x for x in os.listdir(ruta) if x.endswith('.py')])
                lineas.append(f"{prefijo}{'    ' if ult else '│   '}└── ({n} archivos de migración)")
                continue
            lineas.extend(arbol(ruta, prefijo + ("    " if ult else "│   "), nivel + 1, max_nivel))
    return lineas


def funciones(ruta):
    arbol_ast = ast.parse(open(ruta, encoding="utf-8").read())
    return [n.name for n in arbol_ast.body if isinstance(n, ast.FunctionDef)]


# ----------------------------------------------------------------- secciones añadidas
def seccion_config_admin(doc):
    doc.add_heading("6.1 Configuración a nivel de Administrador / Super Usuario", level=2)
    doc.add_paragraph(
        "Tras instalar, el Super Admin (usuario 'admin', rol asignado automáticamente por 'flask seed-inicial') "
        "debe completar esta configuración antes de que el personal use el sistema:")
    tabla(doc, ["#", "Configuración", "Dónde", "Quién", "Detalle"], [
        ("1", "Cambiar la contraseña inicial", "Configuración → Usuarios → editar 'admin'", "Super Admin",
         "La siembra crea admin / admin123; cambiarla de inmediato."),
        ("2", "Crear usuarios por rol", "Configuración → Usuarios → Nuevo Usuario", "Super Admin / Administrador",
         "Asignar Administrador, Supervisor o Cajero; el switch 'Activo' suspende sin borrar."),
        ("3", "Identidad corporativa", "Configuración → Identidad Corporativa (/configuracion/marca)", "Administrador",
         "URL del logo y favicon (se guardan en la tabla configuracion, claves logo_url y favicon_url)."),
        ("4", "Listas de precios", "Configuración → Listas de Precios", "Administrador / Supervisor",
         "Reglas BCV, USDT, Euro y Mayorista: base, operador, porcentaje y moneda."),
        ("5", "Módulos opcionales", "Configuración → Módulos y Funciones", "Administrador",
         "Activa o desactiva Dropshipping (clave modulo_dropshipping_activo)."),
        ("6", "Tasas de cambio", "Configuración → Historial de Tasas", "Administrador",
         "Automáticas (BCV 8:00, USDT cada 4 h); 'Fijar Tasa Manual' como contingencia."),
        ("7", "Catálogo base", "Configuración → Categorías / Atributos; Inventario → Carga Masiva", "Administrador / Supervisor",
         "Crear familias y atributos, luego importar productos desde Excel."),
        ("8", "Contactos", "Configuración → Contactos", "Todos",
         "Clientes y proveedores con tarifa predeterminada para el POS."),
    ], [0.7, 3.5, 4.6, 3, 4.7], tam=8.5)
    doc.add_paragraph("Configuración a nivel de servidor (requiere acceso de administrador del sistema operativo / Docker):")
    tabla(doc, ["Tarea", "Comando o lugar"], [
        ("Clave de sesión y conexión a BD", "Archivo flask_iventario/.env (SECRET_KEY, PG*) o GitHub Environment"),
        ("Retención de PDFs temporales", "Variable RETENCION_PDF_DIAS (por defecto 1 día)"),
        ("Aplicar migraciones", "docker-compose exec inventario_app flask db upgrade"),
        ("Re-sembrar roles y admin", "docker-compose exec inventario_app flask seed-inicial"),
        ("Reiniciar la aplicación", "docker-compose restart inventario_app  (o deploy.yml con action=restart)"),
        ("Ajustar procesos y concurrencia", "CMD de Gunicorn en el Dockerfile: --workers 3 --threads 2 --timeout 120"),
        ("Dominio y HTTPS", "Caddyfile del entorno (proxy inverso hacia inventario_app:5000)"),
    ], [5, 11.5])


def capitulo_archivos(doc, rutas, dir_diag):
    cap = os.path.join(os.path.dirname(dir_diag), "capturas")
    salto(doc)
    doc.add_heading("9. Sistema de Archivos", level=1)
    doc.add_paragraph(
        "SummanPOS maneja cuatro tipos de archivos: los que el usuario sube (Excel de carga masiva), los "
        "reportes que el sistema genera (PDF y Excel), los respaldos de la base de datos y los recursos "
        "estáticos de la interfaz. Todos los archivos persistentes del contenedor viven en el volumen Docker "
        "inventario_uploads, montado en /app/static/uploads.")
    doc.add_heading("9.1 Dónde se almacena cada archivo", level=2)
    tabla(doc, ["Tipo de archivo", "Ubicación", "Lo crea", "Retención", "Acceso"], [
        ("Excel de carga masiva (.xlsx/.csv)", "static/uploads/<uuid>_<nombre>", "Usuario (POST /importar)",
         "Hasta la limpieza", "Admin, Supervisor"),
        ("Reporte de inventario PDF (asíncrono)", "static/uploads/Reporte_Inventario_<fecha>_<uuid>.pdf",
         "Hilo en segundo plano", "RETENCION_PDF_DIAS (1 día)", "Autenticado vía /descargas/<archivo>"),
        ("Reporte de contactos PDF (asíncrono)", "static/uploads/", "Hilo en segundo plano", "RETENCION_PDF_DIAS", "Autenticado"),
        ("Recibos, listas de precios, historial (PDF/Excel)", "Memoria (BytesIO), no se guardan en disco",
         "Petición del usuario", "No persisten", "Según la ruta"),
        ("Respaldos de BD (.sql.gz)", "Google Cloud Storage (bucket del entorno)", "deploy.yml / backup-db",
         "Según política del bucket", "Equipo DevOps"),
        ("Logo y favicon", "URL externa guardada en tabla configuracion", "Administrador", "Permanente", "Público"),
        ("CSS, JS, íconos", "static/css, static/js (imagen Docker)", "Desarrollo", "Versionado en Git", "Público"),
    ], [3.8, 4.4, 2.8, 2.6, 2.9], tam=8)
    doc.add_paragraph(
        "El sistema actual no almacena fotos de perfil de usuarios ni facturas escaneadas: el logo se referencia por "
        "URL y las facturas se generan en PDF a partir de los datos. Si se añadieran, el lugar previsto es el mismo "
        "volumen de uploads, con nombre aleatorio (uuid) y control de acceso por rol.")
    doc.add_heading("9.2 Subida de archivos (carga masiva)", level=2)
    vinetas(doc, [
        "El formulario CargaMasivaForm (Flask-WTF) valida la extensión (.xlsx o .csv) y el token CSRF.",
        "El archivo se guarda con un prefijo uuid4 para evitar colisiones: <uuid>_<nombre original>.",
        "Un hilo en segundo plano lee el Excel con pandas/openpyxl, crea o actualiza productos y registra el movimiento en el kardex.",
        "Al terminar se crea una notificación para el usuario con el resultado.",
    ])
    figura(doc, os.path.join(cap, "53_carga_masiva.png"), "Figura 9.1: Pantalla de carga masiva (/importar)", 15)
    doc.add_heading("9.3 Descarga de reportes", level=2)
    filas = [(" / ".join(r["metodos"]), r["ruta"], ", ".join(r["roles"]))
             for r in rutas if any(k in r["ruta"] for k in ("export", "pdf", "excel", "descarg", "recibo"))]
    tabla(doc, ["Método", "Ruta", "Acceso"], filas, [2.2, 9, 5.3], tam=8.5)
    doc.add_paragraph(
        "Los reportes pequeños (recibos, historial, listas de precios) se generan en memoria con BytesIO y se "
        "envían con send_file, sin tocar el disco. El reporte completo de inventario es pesado y se genera en "
        "segundo plano: la página responde de inmediato y el enlace de descarga llega como notificación.")
    figura(doc, os.path.join(cap, "50_pdf_segundo_plano.png"), "Figura 9.2: Aviso de generación del reporte PDF en segundo plano", 15)
    figura(doc, os.path.join(cap, "52_notificacion_descarga.png"), "Figura 9.3: Notificación con el enlace de descarga del PDF", 15)
    doc.add_heading("9.4 Control de acceso a los archivos", level=2)
    vinetas(doc, [
        ("Autenticación", "/descargas/<archivo> exige sesión iniciada; send_from_directory impide salir de la carpeta uploads (path traversal)."),
        ("Nombres impredecibles", "Los archivos generados llevan un uuid, por lo que no se pueden adivinar."),
        ("Permisos del sistema operativo", "El contenedor corre como usuario no-root 'appuser', dueño solo de /app/static/uploads."),
        ("Persistencia", "El volumen Docker sobrevive a reinicios y redespliegues; restore.yml lo restaura junto con la base."),
        ("Limpieza", "APScheduler borra a las 2:00 a.m. los PDF con más de RETENCION_PDF_DIAS días (services/limpieza_service.py)."),
    ])
    doc.add_paragraph("Recomendaciones:").runs[0].bold = True
    vinetas(doc, [
        "Aplicar secure_filename() al nombre original del Excel antes de guardarlo.",
        "Registrar el dueño de cada reporte para que /descargas solo entregue archivos al usuario que los generó.",
        "Incluir los Excel subidos en la limpieza periódica.",
    ])
    doc.add_heading("9.5 Respaldos de la base de datos", level=2)
    doc.add_paragraph("Los procedimientos de dump y restauración están en la sección 8.1. Resumen del ciclo de vida:")
    vinetas(doc, ["Antes de cada despliegue: pg_dump → .sql.gz → Google Cloud Storage (acción backup-db).",
                  "Verificación: el job falla si el respaldo pesa menos de 1 KB.",
                  "Restauración: restore.yml (base y volumen de uploads) seguida de 'flask db upgrade'."])


def grafico_recursos(csv_ruta, salida, inicio_carga=None):
    import csv as _csv
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    series = {}
    for f in _csv.DictReader(open(csv_ruta, encoding="utf-8")):
        s = series.setdefault(f["contenedor"], {"t": [], "cpu": [], "mem": []})
        s["t"].append(float(f["t"]))
        s["cpu"].append(float(f["cpu_pct"]))
        s["mem"].append(float(f["mem_mb"]))
    colores = {"manual_app": "#2a78d6", "manual_pg": "#eb6834"}
    nombres = {"manual_app": "App Flask/Gunicorn", "manual_pg": "PostgreSQL"}
    fig, ejes = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True)
    for ax, clave, titulo in ((ejes[0], "cpu", "CPU (% de un núcleo)"), (ejes[1], "mem", "Memoria RAM (MB)")):
        for nombre, s in series.items():
            ax.plot(s["t"], s[clave], color=colores.get(nombre, "#555"), linewidth=2, label=nombres.get(nombre, nombre))
            ax.annotate(nombres.get(nombre, nombre), (s["t"][-1], s[clave][-1]), xytext=(4, 0),
                        textcoords="offset points", fontsize=8, color="#333", va="center")
        ax.set_title(titulo, loc="left", fontsize=11, color="#222")
        ax.grid(axis="y", color="#e6e6e6", linewidth=0.8)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        ax.spines["left"].set_color("#bbb")
        ax.spines["bottom"].set_color("#bbb")
        ax.tick_params(colors="#555", labelsize=8)
        if inicio_carga is not None:
            ax.axvline(inicio_carga, color="#999", linestyle="--", linewidth=1)
    ejes[0].legend(frameon=False, fontsize=8, loc="upper left")
    if inicio_carga is not None:
        ejes[0].annotate("inicio de 3 reportes PDF", (inicio_carga, ejes[0].get_ylim()[1] * 0.92),
                         xytext=(4, 0), textcoords="offset points", fontsize=8, color="#555")
    ejes[1].set_xlabel("Segundos desde el inicio del muestreo", fontsize=9, color="#555")
    fig.tight_layout()
    fig.savefig(salida, dpi=170)
    plt.close(fig)


def capitulo_recursos(doc, dir_diag):
    med = os.path.join(os.path.dirname(dir_diag), "mediciones")
    datos = json.load(open(os.path.join(med, "resumen.json"), encoding="utf-8"))
    salto(doc)
    doc.add_heading("10. Procesos y Tareas en Segundo Plano. Gestión de Recursos (CPU, RAM, Disco)", level=1)
    doc.add_heading("10.1 Procesos del sistema", level=2)
    tabla(doc, ["Proceso", "Cantidad", "Función"], [
        ("Gunicorn master", "1", "Recibe conexiones en :5000, crea y vigila a los workers; reinicia los que se cuelgan (timeout 120 s)."),
        ("Gunicorn workers (gthread)", "3 procesos x 2 hilos", "Atienden hasta 6 peticiones simultáneas; cada worker es un proceso Python independiente."),
        ("APScheduler", "1 (solo en un worker)", "Tareas programadas; un candado fcntl sobre scheduler.lock evita que se ejecuten 3 veces."),
        ("Hilos de trabajo (threading.Thread)", "1 por tarea pesada", "Generan PDF grandes e importan Excel sin bloquear la petición."),
        ("PostgreSQL", "1 + procesos auxiliares", "checkpointer, background writer, walwriter, autovacuum y un proceso por conexión."),
        ("Caddy", "1", "Proxy inverso y certificados HTTPS."),
    ], [4.2, 3.3, 9])
    doc.add_heading("Tareas programadas (APScheduler)", level=3)
    tabla(doc, ["Tarea", "Horario", "Archivo", "Recurso que consume"], [
        ("actualizar_bcv", "Diario 8:00 a.m.", "services/bcv_service.py", "Red (scraping BCV), escritura en tasa_cambio"),
        ("actualizar_usdt", "Cada 4 horas", "services/binance_service.py", "Red (API Binance P2P)"),
        ("limpiar_pdfs", "Diario 2:00 a.m.", "services/limpieza_service.py", "Libera disco en static/uploads"),
    ], [3.3, 3.2, 4.8, 5.2])
    doc.add_heading("10.2 Flujo de una tarea en segundo plano", level=2)
    figura(doc, os.path.join(dir_diag, "segundo_plano.png"), "Figura 10.1: Generación asíncrona del reporte PDF de inventario", 15.5)
    doc.add_heading("10.3 Medición real de recursos", level=2)
    doc.add_paragraph(
        f"Medición tomada el {datos['fecha']} con el sistema levantado en Docker Desktop ({datos['host']}), usando la misma "
        "imagen de producción (Gunicorn 3x2), PostgreSQL 15 y 3000 productos de prueba. Herramientas: "
        "agents_scripts/medir_recursos_docker.py (docker stats cada 1-2 s, docker top y psql).")
    tabla(doc, ["Escenario", "CPU app", "RAM app", "RAM PostgreSQL", "Procesos/hilos app", "Observación"],
          [tuple(f) for f in datos["tabla"]], [3.4, 1.8, 2, 2.3, 2.4, 4.6], tam=8.5)
    figura(doc, os.path.join(med, "grafico_recursos.png"),
           "Figura 10.2: CPU y RAM durante la generación simultánea de 3 reportes PDF", 16)
    doc.add_paragraph("Procesos dentro del contenedor (docker top) durante la medición:")
    codigo(doc, datos["docker_top"])
    doc.add_heading("10.4 Cómo gestiona el sistema cada recurso", level=2)
    doc.add_heading("CPU", level=3)
    vinetas(doc, [
        "Concurrencia acotada: 3 workers x 2 hilos = 6 peticiones a la vez; las demás esperan en la cola del socket.",
        "Las tareas pesadas (PDF masivo, importación) se sacan del ciclo de la petición hacia hilos, por lo que la página responde en "
        f"{datos['respuesta_ms']} ms aunque el PDF tarde mucho más.",
        "Por el GIL de Python, varios hilos en el mismo worker comparten un núcleo: en la medición el contenedor se mantuvo cerca del "
        "100 % (un núcleo) aun con 3 reportes a la vez.",
        "--timeout 120 reinicia un worker que se bloquea, protegiendo al resto.",
    ])
    doc.add_heading("Memoria RAM", level=3)
    vinetas(doc, [
        "Cada worker carga la aplicación completa (~130-145 MB RSS en reposo).",
        "Paginación con .paginate() en los listados (productos, contactos, atributos, tasas...) para no cargar tablas completas.",
        "Los reportes pequeños se generan en memoria (BytesIO) y se liberan al enviarse.",
        "El renderizado de PDF masivo es el mayor consumo: la medición muestra el pico de RAM durante esa tarea.",
        "Hallazgo de la medición: el worker que generó los PDF quedó con ~1,15 GB aun después de terminar. "
        "Recomendación: añadir '--max-requests 500 --max-requests-jitter 50' a Gunicorn para reciclar workers y liberar esa memoria.",
        "Recomendación: fijar un límite en docker-compose (deploy.resources.limits.memory, p. ej. 2 GB) para que un pico no afecte a otros servicios del VPS.",
    ])
    doc.add_heading("Disco", level=3)
    vinetas(doc, [
        f"Base de datos de prueba: {datos['bd_tamano']} con 3000 productos; la imagen Docker ocupa {datos['imagen']} (construcción multi-etapa sin compiladores).",
        "Los PDF temporales se eliminan cada noche (RETENCION_PDF_DIAS).",
        "rsync --delete en cada despliegue evita archivos y migraciones obsoletas en el servidor.",
        "Los respaldos se suben a Google Cloud Storage en lugar de acumularse en el disco del VPS.",
        "Logs en stdout del contenedor: rotarlos con la configuración de logging de Docker (max-size).",
    ])
    doc.add_heading("10.5 Comandos de monitoreo", level=2)
    codigo(doc, "docker stats                                  # CPU, RAM, red y disco por contenedor en vivo\n"
                "docker top <contenedor> -o pid,nlwp,pcpu,rss,args  # procesos e hilos\n"
                "docker system df -v                           # espacio de imágenes, contenedores y volúmenes\n"
                "htop  |  free -m  |  df -h                    # recursos del servidor\n"
                "python agents_scripts/medir_recursos_docker.py muestreo --segundos 60 --salida muestreo.csv")


# ----------------------------------------------------------------- documento
def construir(meta, dir_diag, version, autor, institucion, materia):
    doc = docx.Document()
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(11)
    for nombre, tam, color in (("Heading 1", 18, MORADO), ("Heading 2", 14, OSCURO), ("Heading 3", 12, MORADO)):
        h = doc.styles[nombre]
        h.font.name = "Calibri"
        h.font.size = Pt(tam)
        h.font.color.rgb = color
        h.font.bold = True
    s0 = doc.sections[0]
    s0.page_width, s0.page_height = Cm(21), Cm(29.7)
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(s0, m, Cm(2))

    tablas = meta["tablas"]
    rutas = meta["rutas"]
    hoy = date.today().strftime("%d/%m/%Y")

    # --- Página de título interna + índice
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MANUAL TÉCNICO")
    r.bold, r.font.size, r.font.color.rgb = True, Pt(28), MORADO
    p = doc.add_paragraph("SummanPOS — Sistema de Punto de Venta e Inventario Multimoneda")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].font.size = Pt(14)
    doc.add_paragraph()
    p = doc.add_paragraph()
    r = p.add_run("Índice")
    r.bold, r.font.size, r.font.color.rgb = True, Pt(18), MORADO
    toc(doc)
    salto(doc)

    # ===================== 1
    doc.add_heading("1. Portada e Introducción", level=1)
    doc.add_heading("1.1 Datos del proyecto", level=2)
    tabla(doc, ["Campo", "Valor"], [
        ("Nombre del sistema", "SummanPOS (InvenTrack Pro) — Mini-ERP y Punto de Venta"),
        ("Versión", version),
        ("Autor(es)", autor),
        ("Fecha", hoy),
        ("Materia", materia),
        ("Institución", institucion),
        ("Repositorio / aplicación", "flask_iventario/ (aplicación activa); flask_api/ es una versión anterior"),
        ("URL del entorno de pruebas", "https://dev-mini-erp.summantech.com/"),
    ], [5, 11])
    doc.add_heading("1.2 Propósito del manual", level=2)
    doc.add_paragraph(
        "Este documento describe la construcción interna de SummanPOS. Está dirigido a desarrolladores, "
        "administradores de sistemas y personal de soporte técnico que necesiten instalar, configurar, "
        "desplegar, mantener o ampliar el sistema. Reúne el stack tecnológico, la arquitectura, el modelo "
        "de datos, la estructura del código, las rutas HTTP, los mecanismos de seguridad y los "
        "procedimientos de respaldo y solución de problemas. Para el uso diario de las pantallas debe "
        "consultarse el Manual de Usuario.")
    doc.add_heading("1.3 Descripción general del sistema", level=2)
    doc.add_paragraph(
        "SummanPOS es una aplicación web para comercios de repuestos y comercio general en Venezuela. "
        "Resuelve el problema de vender, comprar y controlar inventario en un entorno multimoneda, donde "
        "cada operación se cotiza en dólares pero se cobra en bolívares (tasa BCV), euros o USDT, y debe "
        "aplicar IVA (16%) e IGTF (3%).")
    doc.add_paragraph("Alcance funcional:")
    vinetas(doc, [
        ("Inventario", "catálogo de productos con categorías, atributos dinámicos, kardex, papelera y carga masiva desde Excel."),
        ("Punto de venta", "ventas al contado y a crédito con múltiples métodos de pago y guía de despacho imprimible."),
        ("Compras", "órdenes de compra a proveedores con recepción parcial de mercancía."),
        ("Finanzas", "cuentas por cobrar y por pagar, abonos con calculadora en bolívares e historial de pagos."),
        ("Tasas de cambio", "actualización automática BCV (USD/EUR) y Binance USDT, con fijación manual de contingencia."),
        ("Listas de precios", "reglas por moneda (BCV, USDT, Euro, Mayorista) y precios excepcionales por producto."),
        ("Administración", "usuarios y roles, identidad corporativa, módulos opcionales (Dropshipping) y notificaciones."),
    ])

    # ===================== 2
    salto(doc)
    doc.add_heading("2. Requisitos y Entorno de Desarrollo (Stack Tecnológico)", level=1)
    doc.add_heading("2.1 Requisitos de hardware", level=2)
    doc.add_paragraph("Valores recomendados según la configuración de despliegue (Gunicorn con 3 workers x 2 hilos y PostgreSQL):")
    tabla(doc, ["Componente", "Servidor (mínimo)", "Servidor (recomendado)", "Cliente (estación de caja)"], [
        ("Procesador", "2 vCPU x86_64", "4 vCPU", "Doble núcleo 2 GHz"),
        ("Memoria RAM", "2 GB", "4 GB o más", "4 GB"),
        ("Almacenamiento", "20 GB SSD", "40 GB SSD (respaldos y uploads)", "Sin requisito (aplicación web)"),
        ("Red", "IP pública + dominio con HTTPS", "Ancho de banda 50 Mbps", "Conexión a internet estable"),
        ("Periféricos", "—", "—", "Impresora para guías; lector de código de barras opcional"),
        ("Pantalla", "—", "—", "Resolución mínima 1366x768"),
    ], [3.5, 3.8, 4.2, 4.5])
    doc.add_heading("2.2 Requisitos de software", level=2)
    doc.add_heading("Sistemas operativos compatibles", level=3)
    vinetas(doc, [
        ("Servidor de producción", "Linux (Ubuntu Server 22.04/24.04 LTS o Debian 12) con Docker y Docker Compose. La imagen se basa en python:3.14-slim (Debian)."),
        ("Desarrollo", "Windows 10/11, macOS o Linux con Python 3.12+ o Docker Desktop."),
        ("Cliente", "Cualquier sistema con navegador moderno: Chrome, Edge o Firefox actualizados."),
    ])
    doc.add_heading("Lenguajes, base de datos y herramientas", level=3)
    tabla(doc, ["Tecnología", "Versión", "Uso"], [
        ("Python", "3.14 (imagen Docker)", "Lenguaje del backend"),
        ("HTML5 / CSS3 / JavaScript", "ES6", "Interfaz (plantillas Jinja2)"),
        ("PostgreSQL", "15 o superior (CI usa 15; respaldos con cliente 18)", "Gestor de base de datos relacional"),
        ("Docker / Docker Compose", "24+ / v2", "Contenedorización y orquestación"),
        ("Gunicorn", "26.0.0", "Servidor WSGI de producción"),
        ("Caddy", "2.x", "Proxy inverso con HTTPS automático"),
        ("GitHub Actions", "—", "CI/CD: migraciones, despliegue, respaldo y escaneo de seguridad"),
    ], [5, 5.5, 6])
    doc.add_heading("Frameworks, librerías y dependencias", level=3)
    tabla(doc, ["Paquete", "Versión", "Propósito"], [
        ("Flask", "3.1.3", "Framework web (rutas, blueprints, plantillas)"),
        ("Flask-SQLAlchemy / SQLAlchemy", "3.1.1 / 2.0.51", "ORM y acceso a datos"),
        ("Flask-Migrate / Alembic", "4.1.0 / 1.18.5", "Migraciones versionadas del esquema"),
        ("Flask-Login", "0.6.3", "Gestión de sesiones de usuario"),
        ("Flask-Bcrypt / bcrypt", "1.0.1 / 5.0.0", "Hash de contraseñas"),
        ("Flask-WTF / WTForms", "1.3.0 / 3.2.2", "Formularios con validación y CSRF"),
        ("Flask-APScheduler", "última", "Tareas programadas (tasas, limpieza)"),
        ("psycopg2-binary", "2.9.12", "Driver PostgreSQL"),
        ("pandas / openpyxl / xlsxwriter", "3.0.5 / 3.1.5 / última", "Importación y exportación Excel"),
        ("WeasyPrint / xhtml2pdf", "69.0 / última", "Generación de PDF (recibos, reportes)"),
        ("requests / beautifulsoup4", "última", "Consulta de tasas BCV y Binance"),
        ("python-dotenv", "1.2.2", "Carga de variables desde .env"),
        ("Bootstrap / Bootstrap Icons", "5.3.2 / 1.11.1", "Estilos y componentes de interfaz (CDN)"),
        ("Tom-Select, SweetAlert2, Chart.js, Animate.css", "2.2.2 / 11 / — / 4.1.1", "Buscadores, alertas, gráficas y animaciones"),
    ], [5.5, 4, 7])

    # ===================== 3
    salto(doc)
    doc.add_heading("3. Arquitectura del Sistema", level=1)
    doc.add_heading("3.1 Diagrama de arquitectura", level=2)
    doc.add_paragraph(
        "El navegador solicita páginas y datos JSON por HTTPS. Caddy termina TLS y reenvía al contenedor "
        "inventario_app, donde Gunicorn ejecuta la aplicación Flask. Los controladores delegan la lógica en "
        "la capa de servicios, que usa los modelos SQLAlchemy para leer y escribir en PostgreSQL. "
        "APScheduler consulta periódicamente al BCV y a Binance.")
    figura(doc, os.path.join(dir_diag, "arquitectura.png"), "Figura 3.1: Arquitectura cliente-servidor de SummanPOS", 14.5)
    doc.add_heading("3.2 Patrón de diseño", level=2)
    doc.add_paragraph(
        "SummanPOS sigue una arquitectura Cliente-Servidor monolítica modular, organizada con el patrón "
        "MVC (Modelo-Vista-Controlador) extendido con una capa de servicios:")
    vinetas(doc, [
        ("Modelo", "models.py — clases SQLAlchemy que representan las tablas y sus relaciones."),
        ("Vista", "templates/*.html — plantillas Jinja2 renderizadas en el servidor con Bootstrap."),
        ("Controlador", "routes/*_routes.py — Blueprints de Flask que reciben la petición, validan permisos y devuelven HTML o JSON."),
        ("Servicios", "services/*_service.py — reglas de negocio reutilizables (cálculos fiscales, stock, abonos)."),
        ("Application Factory", "create_app() en app.py crea y configura la aplicación, facilitando pruebas y distintos entornos."),
        ("Decorator", "@rol_requerido y @login_required aplican autorización de forma declarativa."),
    ])
    doc.add_paragraph(
        "Cada módulo funcional (inventario, ventas, compras, finanzas...) es un Blueprint independiente, "
        "lo que permite activar o desactivar módulos (p. ej. Dropshipping) sin afectar al resto.")

    # ===================== 4
    salto(doc)
    doc.add_heading("4. Diseño de Base de Datos", level=1)
    doc.add_heading("4.1 Diagrama Entidad-Relación (DER)", level=2)
    doc.add_paragraph(
        f"El esquema contiene {len(tablas)} tablas generadas por migraciones Alembic a partir de models.py. "
        "Se presentan dos vistas por área y, en la página siguiente, el modelo completo.")
    figura(doc, os.path.join(dir_diag, "der_inventario.png"), "Figura 4.1: DER — Catálogo e inventario (todas las columnas)", 16.5)
    figura(doc, os.path.join(dir_diag, "der_operaciones.png"), "Figura 4.2: DER — Ventas, compras, finanzas y usuarios (columnas clave)", 16.5)
    nueva_seccion(doc, horizontal=True)
    figura(doc, os.path.join(dir_diag, "der.png"), "Figura 4.3: DER completo del sistema (PK y FK)", 25.5)
    nueva_seccion(doc, horizontal=False)
    doc.add_heading("4.2 Diccionario de datos", level=2)
    doc.add_paragraph("Generado automáticamente desde los modelos SQLAlchemy (tipos según el dialecto SQL estándar).")
    for t in tablas:
        doc.add_heading(f"Tabla: {t['tabla']}", level=3)
        doc.add_paragraph(DESC_TABLAS.get(t["tabla"], ""))
        filas = []
        for c in t["columnas"]:
            restr = list(c["restricciones"])
            if c["default"] and c["default"] not in ("None",):
                restr.append(f"DEFAULT {c['default']}")
            desc = DESC_ESPECIFICAS.get((t["tabla"], c["nombre"])) or DESC_COLS.get(c["nombre"]) or (
                "Llave foránea." if any(r.startswith("FK") for r in restr) else "—")
            filas.append((c["nombre"], c["tipo"], ", ".join(restr) or "NULL", desc))
        tabla(doc, ["Campo", "Tipo de dato", "Restricciones", "Descripción"], filas, [3.6, 3.2, 4.2, 6], tam=8.5)
        if t["unique_compuestos"]:
            doc.add_paragraph("Restricción UNIQUE compuesta: " + "; ".join("(" + ", ".join(u) + ")" for u in t["unique_compuestos"]))

    # ===================== 5
    salto(doc)
    doc.add_heading("5. Estructura del Código / Módulos", level=1)
    doc.add_heading("5.1 Árbol de directorios", level=2)
    raiz = ["SummanPOS/", "├── .github/workflows/   (CI/CD: check_migrations, deploy, db_migrations, restore, security)",
            "├── agents_scripts/      (scripts auxiliares de diagnóstico y documentación)",
            "├── directives/          (procedimientos operativos en Markdown)",
            "├── docs/                (manuales de usuario y técnico)",
            "├── scripts/             (herramientas permanentes: scan_secrets, install_hooks)",
            "├── flask_api/           (versión anterior, no activa)",
            "└── flask_iventario/     (APLICACIÓN ACTIVA)"]
    codigo(doc, "\n".join(raiz + ["    " + l for l in arbol(APP, max_nivel=1)]))
    doc.add_heading("5.2 Descripción de módulos y controladores", level=2)
    filas = []
    for archivo, desc in DESC_MODULOS.items():
        ruta = os.path.join(APP, archivo)
        fn = ", ".join(funciones(ruta)[:14]) if os.path.isfile(ruta) and archivo.endswith(".py") else ""
        filas.append((archivo, desc, fn or "—"))
    tabla(doc, ["Archivo", "Responsabilidad", "Funciones principales"], filas, [4, 7, 6], tam=8.5)
    doc.add_heading("Capa de servicios", level=3)
    filas = []
    for f in sorted(os.listdir(os.path.join(APP, "services"))):
        if f.endswith("_service.py") or f.endswith("_services.py"):
            filas.append((f, ", ".join(funciones(os.path.join(APP, "services", f)))))
    tabla(doc, ["Archivo", "Funciones"], filas, [5, 12], tam=8.5)
    doc.add_heading("5.3 Rutas y endpoints", level=2)
    doc.add_paragraph(
        f"La aplicación expone {len(rutas)} rutas agrupadas en blueprints. Las respuestas 'HTML/Redirect' "
        "devuelven una plantilla o redirigen tras procesar un formulario; las 'JSON' son APIs internas "
        "consumidas con fetch() desde el navegador. Parámetros: form = campo de formulario POST, "
        "args = query string, files = archivo subido, json = cuerpo JSON; los segmentos <...> son parámetros de ruta.")
    por_bp = {}
    for r in rutas:
        por_bp.setdefault(r["blueprint"], []).append(r)
    for bp, lista in por_bp.items():
        doc.add_heading(f"Blueprint: {bp} ({lista[0]['archivo']})", level=3)
        filas = [(" / ".join(r["metodos"]), r["ruta"], r["funcion"], ", ".join(r["roles"]),
                  ", ".join(r["parametros"]) or "—", r["respuesta"]) for r in lista]
        tabla(doc, ["Método", "Ruta", "Función", "Acceso", "Parámetros de entrada", "Salida"],
              filas, [1.6, 4.2, 3.2, 2.8, 3.7, 1.8], tam=7.5)

    # ===================== 6
    salto(doc)
    doc.add_heading("6. Instalación, Configuración y Despliegue", level=1)
    doc.add_heading("Paso 1 — Clonar el repositorio", level=2)
    codigo(doc, "git clone https://github.com/SummanTech/SummanPOS.git\ncd SummanPOS/flask_iventario")
    doc.add_heading("Paso 2 — Variables de entorno (.env)", level=2)
    doc.add_paragraph("Crear flask_iventario/.env (nunca se sube al repositorio). Variables usadas por app.py y docker-compose.yml:")
    tabla(doc, ["Variable", "Ejemplo", "Descripción"], [
        ("SECRET_KEY", "<cadena aleatoria larga>", "Firma de cookies de sesión y tokens CSRF (obligatoria en producción)"),
        ("PGHOST", "localhost / nombre del contenedor", "Servidor PostgreSQL"),
        ("PGPORT", "5432", "Puerto de PostgreSQL"),
        ("PGDATABASE", "flask_inventario_db", "Nombre de la base de datos"),
        ("PGUSER", "summanpos", "Usuario de la base de datos"),
        ("PGPASSWORD", "<secreto>", "Contraseña de la base de datos"),
        ("PGSSLMODE", "prefer", "Modo SSL de la conexión (opcional)"),
        ("ENV_FOLDER", "dev", "Entorno: nombra el proyecto Compose y la red <env>_shared_net"),
        ("RETENCION_PDF_DIAS", "1", "Días que se conservan los PDF temporales en static/uploads"),
        ("SKIP_DB_BOOTSTRAP", "true", "Omite la siembra automática al arrancar (opcional)"),
    ], [3.6, 4.6, 8.3])
    codigo(doc, "SECRET_KEY=cambia-esto-por-una-clave-larga\nPGHOST=localhost\nPGPORT=5432\n"
                "PGDATABASE=flask_inventario_db\nPGUSER=summanpos\nPGPASSWORD=********\nENV_FOLDER=dev")
    doc.add_heading("Paso 3 — Instalar dependencias", level=2)
    doc.add_paragraph("Opción A, entorno local con Python:")
    codigo(doc, "python -m venv .venv\n# Windows: .venv\\Scripts\\activate   |   Linux: source .venv/bin/activate\n"
                "pip install -r requirements.txt")
    doc.add_paragraph("Opción B, Docker (recomendada; incluye las librerías de sistema de WeasyPrint):")
    codigo(doc, "docker network create dev_shared_net     # una sola vez\ndocker-compose build")
    doc.add_heading("Paso 4 — Crear y migrar el esquema de base de datos", level=2)
    doc.add_paragraph("El esquema se construye solo con migraciones Alembic (nunca con db.create_all()):")
    codigo(doc, "createdb -U postgres flask_inventario_db      # crear la base vacía\n"
                "set FLASK_APP=app.py                          # Linux: export FLASK_APP=app.py\n"
                "flask db upgrade                              # aplica migrations/versions\n"
                "flask seed-inicial                            # roles + usuario admin inicial")
    doc.add_paragraph("Si se modifica un modelo, generar la migración en el mismo cambio (lo verifica check_migrations.yml):")
    codigo(doc, 'flask db migrate -m "Descripcion del cambio"\nflask db upgrade')
    doc.add_heading("Paso 5 — Iniciar el servidor", level=2)
    codigo(doc, "# Desarrollo (recarga automática, http://127.0.0.1:5000)\npython app.py\n\n"
                "# Producción con Gunicorn\ngunicorn --bind 0.0.0.0:5000 --workers 3 --threads 2 --timeout 120 app:app\n\n"
                "# Producción con Docker\ndocker-compose up -d --build\ndocker-compose exec inventario_app flask db upgrade\n"
                "docker-compose exec inventario_app flask seed-inicial")
    doc.add_heading("Despliegue automatizado (GitHub Actions)", level=2)
    doc.add_paragraph("La rama define el entorno (main → prd; dev/uat → carpeta homónima en /opt/deploy/<env>/). "
                      "Los despliegues son manuales (workflow_dispatch) con deploy.yml, que:")
    vinetas(doc, ["Sincroniza el código con rsync --delete (evita migraciones obsoletas).",
                  "Genera el .env desde variables y secretos del GitHub Environment.",
                  "Construye y levanta el contenedor en la red <env>_shared_net.",
                  "Respalda la base (pg_dump → Google Cloud Storage) antes de migrar.",
                  "Ejecuta flask db upgrade, flask db check y flask seed-inicial.",
                  "Verifica la salud del servicio contra /login (10 intentos)."])
    seccion_config_admin(doc)

    # ===================== 7
    salto(doc)
    doc.add_heading("7. Seguridad y Permisos", level=1)
    doc.add_heading("7.1 Autenticación y autorización", level=2)
    vinetas(doc, [
        ("Sesiones por cookie", "Flask-Login guarda el id del usuario en una cookie de sesión firmada con SECRET_KEY; "
                                "user_loader recarga el usuario en cada petición."),
        ("Hash de contraseñas", "Bcrypt (Flask-Bcrypt) con sal aleatoria; en la tabla usuarios solo se guarda password_hash."),
        ("Protección de vistas", "@login_required y before_request por blueprint redirigen a /login si no hay sesión."),
        ("Autorización por rol", "@rol_requerido('Administrador', 'Supervisor') compara el rol del usuario; Super Admin siempre pasa."),
        ("CSRF", "Los formularios Flask-WTF (p. ej. login) incluyen token CSRF."),
        ("Usuarios inactivos", "El campo usuarios.activo permite suspender cuentas sin borrar su historial."),
        ("Infraestructura", "HTTPS vía Caddy, contenedor con usuario no-root, secretos solo en .env/GitHub Secrets, "
                            "escaneo de secretos (Trivy, TruffleHog, scan_secrets.py) en cada push."),
    ])
    doc.add_paragraph("Recomendaciones detectadas al revisar el código:").runs[0].bold = True
    vinetas(doc, [
        "Definir SECRET_KEY en el .env de cada entorno: si falta, app.py usa el valor por defecto 'default_secret'.",
        "Cambiar la contraseña del usuario 'admin' creado por la siembra inicial (admin123) tras la instalación.",
        "Activar CSRFProtect global para cubrir también los formularios HTML y llamadas fetch que no usan Flask-WTF.",
        "Validar el parámetro 'next' del login para evitar redirecciones abiertas.",
    ])
    doc.add_heading("7.2 Roles de usuario", level=2)
    tabla(doc, ["Rol", "Nivel de acceso"], ROLES, [3.5, 13])
    conteo = {}
    for r in rutas:
        for rol in r["roles"]:
            conteo[rol] = conteo.get(rol, 0) + 1
    doc.add_paragraph("Rutas que mencionan explícitamente cada rol: " +
                      ", ".join(f"{k}: {v}" for k, v in sorted(conteo.items())) + ".")

    # ===================== 8
    salto(doc)
    doc.add_heading("8. Mantenimiento y Solución de Problemas", level=1)
    doc.add_heading("8.1 Gestión de respaldos (backups)", level=2)
    doc.add_paragraph("Respaldo manual con pg_dump (formato SQL comprimido):")
    codigo(doc, "pg_dump -h $PGHOST -U $PGUSER -d flask_inventario_db | gzip > respaldo_$(date +%F).sql.gz\n\n"
                "# Desde Docker, sin instalar el cliente:\ndocker run --rm --network dev_shared_net -e PGPASSWORD=$PGPASSWORD postgres:18-alpine \\\n"
                "  pg_dump -h $PGHOST -U $PGUSER flask_inventario_db | gzip > respaldo.sql.gz")
    doc.add_paragraph("Restauración:")
    codigo(doc, "gunzip -c respaldo_2026-11-11.sql.gz | psql -h $PGHOST -U $PGUSER -d flask_inventario_db\n"
                "flask db upgrade      # alinear el esquema si el respaldo es de una versión anterior")
    vinetas(doc, [
        ("Automático", "deploy.yml ejecuta la acción backup-db antes de cada migración y sube el .sql.gz a Google Cloud Storage."),
        ("Restauración en servidor", "restore.yml restaura la base y el volumen de archivos (uploads) de una fecha elegida."),
        ("Archivos subidos", "El volumen Docker inventario_uploads (static/uploads) contiene logos y PDFs; respaldarlo junto con la base."),
    ])
    doc.add_heading("8.2 Logs y bitácoras", level=2)
    tabla(doc, ["Fuente", "Ubicación / comando", "Contenido"], [
        ("Aplicación y Gunicorn", "docker-compose logs -f inventario_app", "Peticiones, errores 500 y app.logger (stdout/stderr)"),
        ("Desarrollo local", "Consola donde corre python app.py", "Trazas con depurador de Flask (debug=True)"),
        ("Tareas programadas", "Mismos logs del contenedor", "Resultados de actualización BCV/USDT y limpieza de PDFs"),
        ("Kardex (auditoría)", "Tabla transacciones / pantalla /transacciones", "Historial inmutable de movimientos de stock"),
        ("Notificaciones", "Tabla notificaciones / /notificaciones", "Alertas del sistema por usuario"),
        ("CI/CD", "GitHub → Actions → registro de cada workflow", "Despliegues, migraciones, respaldos y escaneos"),
        ("Base de datos", "Logs del servidor PostgreSQL", "Errores de conexión y consultas"),
    ], [3.5, 6, 7])
    doc.add_heading("8.3 Errores comunes y soluciones", level=2)
    tabla(doc, ["Síntoma", "Causa", "Solución"], ERRORES, [5, 5.5, 6], tam=8.5)

    capitulo_archivos(doc, rutas, dir_diag)
    capitulo_recursos(doc, dir_diag)
    doc.core_properties.title = "Manual Técnico del Sistema SummanPOS"
    doc.core_properties.author = autor
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadatos", required=True)
    ap.add_argument("--diagramas", required=True)
    ap.add_argument("--portada", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--version", default="2.0 (noviembre 2026)")
    ap.add_argument("--autor", default="Claudio Viera — Sección B")
    ap.add_argument("--institucion", default="Instituto Universitario Jesús Obrero — Extensión Barquisimeto")
    ap.add_argument("--materia", default="Sistemas Operativos")
    a = ap.parse_args()
    meta = json.load(open(a.metadatos, encoding="utf-8"))
    doc = construir(meta, a.diagramas, a.version, a.autor, a.institucion, a.materia)
    insertar_portada(doc, a.portada, "Cableado de Redes", a.materia + ":", "Manual Técnico del Sistema SummanPOS")
    os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
    doc.save(a.salida)
    print("OK ->", a.salida)


if __name__ == "__main__":
    main()
