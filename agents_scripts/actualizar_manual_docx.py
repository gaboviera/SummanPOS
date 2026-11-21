"""Actualiza el Manual de Usuario de SummanPOS (.docx).

- Reemplaza las capturas del manual por las nuevas (carpeta --capturas).
- Inserta una portada institucional (otro .docx) como primera página, en su propia sección.
- Cambia el título de la portada (párrafo que contiene --titulo-buscar).
- Agrega la sección "Módulos y Funciones" y una nota sobre Dropshipping.

Uso:
    python agents_scripts/actualizar_manual_docx.py \
        --manual docs/manual_usuario/Manual_Usuario_SummanPOS.docx \
        --portada "C:/ruta/PortadaIujo.docx" \
        --capturas docs/manual_usuario/screenshots \
        --salida docs/manual_usuario/Manual_Usuario_SummanPOS.docx
"""
import argparse
import copy
import json
import os
import sys

import docx
from docx.oxml.ns import qn
from PIL import Image

# Orden de las imágenes tal como aparecen en el manual -> archivo de captura.
# None = conservar la imagen existente (p.ej. Dropshipping, módulo desactivado en el sistema).
ORDEN_CAPTURAS = [
    "01_landing_page", "02_login_seguridad", "25_configuracion_usuarios",
    "26_usuario_modal_nuevo", "27_usuario_modal_llenado", "28_usuario_modal_editar",
    "03_dashboard_gerencial", "04_inventario_catalogo", "05_inventario_nuevo_producto",
    "43_inventario_editar_producto", "06_inventario_lista_precios",
    "47_lista_precios_selector_columnas", "46_lista_precios_modal_exportar",
    "07_inventario_kardex_movimientos", "08_inventario_carga_masiva",
    "09_pos_punto_de_venta", "09_pos_modal_cobro", "10_pos_historial_ventas",
    "40_ventas_recibo_impresion", "11_compras_ordenes", "12_compras_nueva_orden",
    "37_compras_recibir_mercancia", "38_compras_recibo_detalle",
    None, None, None, None,  # Dropshipping
    "16_finanzas_cxc", "33_cxc_modal_abono", "34_cxc_modal_calculadora",
    "35_cxc_modal_historial", "17_finanzas_cxp", "36_cxp_modal_abono",
    "18_finanzas_historial_pagos", "19_configuracion_contactos",
    "29_contacto_modal_nuevo", "30_contacto_modal_llenado",
    "20_configuracion_categorias", "31_categoria_modal_editar",
    "21_configuracion_atributos", "32_atributos_gestion_valores",
    "22_configuracion_tasas_bcv", "42_tasas_bcv_fijacion_manual",
    "23_configuracion_marca", "24_configuracion_listas_precios",
    "41_lista_precios_modal_nueva", "45_notificaciones_historial",
]

NOTA_DROPSHIPPING = (
    "Nota: Dropshipping es un módulo opcional. Se activa o desactiva desde "
    "Configuración → Módulos y Funciones; mientras está desactivado, sus menús y "
    "opciones se ocultan en toda la aplicación. Las imágenes de este capítulo "
    "muestran el módulo con la opción activada."
)
TEXTO_MODULOS = (
    "Desde Configuración → Módulos y Funciones (/configuracion/modulos) el "
    "Administrador activa o desactiva los módulos avanzados según el modelo de negocio. "
    "Actualmente controla el Módulo de Dropshipping: al desactivarlo, la mercancía se "
    "gestiona solo con inventario físico propio y las opciones de dropshipping se "
    "ocultan en menús y ventas. Los cambios se aplican con el botón 'Guardar Cambios'."
)


def texto(p):
    return "".join(t.text or "" for t in p.iter(qn("w:t")))


def poner_texto(p, nuevo):
    runs = p.findall(qn("w:r"))
    con_texto = [r for r in runs if r.find(qn("w:t")) is not None]
    if not con_texto:
        raise ValueError("párrafo sin runs de texto")
    con_texto[0].find(qn("w:t")).text = nuevo
    for r in con_texto[1:]:
        p.remove(r)


def reemplazar_capturas(doc, carpeta):
    body = doc.element.body
    blips = list(body.iter(qn("a:blip")))
    if len(blips) != len(ORDEN_CAPTURAS):
        sys.exit(f"El manual tiene {len(blips)} imágenes, se esperaban {len(ORDEN_CAPTURAS)}")
    for blip, nombre in zip(blips, ORDEN_CAPTURAS):
        if nombre is None:
            continue
        ruta = os.path.join(carpeta, nombre + ".png")
        rid, _ = doc.part.get_or_add_image(ruta)
        blip.set(qn("r:embed"), rid)
        inline = blip
        while inline.tag not in (qn("wp:inline"), qn("wp:anchor")):
            inline = inline.getparent()
        ext = inline.find(qn("wp:extent"))
        w, h = Image.open(ruta).size
        cx = int(ext.get("cx"))
        cy = int(cx * h / w)
        ext.set("cy", str(cy))
        for e in inline.iter(qn("a:ext")):
            e.set("cy", str(cy))
    # eliminar relaciones de imagen huérfanas
    usados = {b.get(qn("r:embed")) for b in body.iter(qn("a:blip"))}
    for rid, rel in list(doc.part.rels.items()):
        if rel.reltype.endswith("/image") and rid not in usados:
            doc.part.drop_rel(rid)


def parrafos_figura(body):
    """Devuelve [(parrafo_imagen, parrafo_caption)] en orden."""
    ps = list(body.iter(qn("w:p")))
    res = []
    for i, p in enumerate(ps):
        if p.find(".//" + qn("a:blip")) is not None:
            cap = next(q for q in ps[i + 1:i + 4] if texto(q).strip())
            res.append((p, cap))
    return res


def agregar_secciones(doc, carpeta):
    body = doc.element.body
    ps = list(body.iter(qn("w:p")))
    figs = parrafos_figura(body)

    def buscar(prefijo):
        return next(p for p in ps if texto(p).strip().startswith(prefijo))

    # --- Nota en Dropshipping (después del primer párrafo de texto del capítulo 7)
    cap7 = buscar("Capítulo 7:")
    idx = ps.index(cap7)
    cuerpo = next(q for q in ps[idx + 1:] if texto(q).strip())
    nota = copy.deepcopy(cuerpo)
    poner_texto(nota, NOTA_DROPSHIPPING)
    for r in nota.iter(qn("w:r")):
        rpr = r.find(qn("w:rPr"))
        if rpr is None:
            rpr = r.makeelement(qn("w:rPr"), {})
            r.insert(0, rpr)
        if rpr.find(qn("w:i")) is None:
            rpr.append(rpr.makeelement(qn("w:i"), {}))
    cuerpo.addnext(nota)

    # --- Nueva sección 9.5 Módulos y Funciones (tras la última figura del cap. 9)
    sub = buscar("9.4") if any(texto(p).strip().startswith("9.4") for p in ps) else \
        [p for p in ps if texto(p).strip()[:2] == "9." ][-1]
    img_ref, cap_ref = figs[ORDEN_CAPTURAS.index("41_lista_precios_modal_nueva")]
    titulo = copy.deepcopy(sub)
    poner_texto(titulo, "9.5 Módulos y Funciones del Sistema (/configuracion/modulos)")
    parrafo = copy.deepcopy(nota)
    poner_texto(parrafo, TEXTO_MODULOS)
    for i_el in parrafo.iter(qn("w:i")):
        i_el.getparent().remove(i_el)
    img = copy.deepcopy(img_ref)
    ruta = os.path.join(carpeta, "48_configuracion_modulos.png")
    rid, _ = doc.part.get_or_add_image(ruta)
    img.find(".//" + qn("a:blip")).set(qn("r:embed"), rid)
    inline = img.find(".//" + qn("wp:inline"))
    ext = inline.find(qn("wp:extent"))
    w, h = Image.open(ruta).size
    cy = int(int(ext.get("cx")) * h / w)
    ext.set("cy", str(cy))
    for e in inline.iter(qn("a:ext")):
        e.set("cy", str(cy))
    docpr = inline.find(qn("wp:docPr"))
    docpr.set("id", "4801")
    docpr.set("name", "Modulos")
    cap = copy.deepcopy(cap_ref)
    poner_texto(cap, "Figura: Control de Módulos Opcionales (Activación del Módulo de Dropshipping)")
    ancla = cap_ref
    for el in (titulo, parrafo, img, cap):
        ancla.addnext(el)
        ancla = el

    # --- Índice: capítulo 9
    for p in ps:
        t = texto(p)
        if t.strip().startswith("▪") and "Capítulo 9:" in t:
            poner_texto(p, t.replace("Marca y Listas)", "Marca, Listas y Módulos)"))


PANTALLAS_ROL = [
    ("/ventas", "Punto de Venta"), ("/ventas/historial", "Historial de Ventas"),
    ("/productos", "Productos (consulta)"), ("/productos/nuevo", "Crear / editar productos"),
    ("/productos/lista-precios", "Lista de Precios al Consumidor"), ("/transacciones", "Movimientos (Kardex)"),
    ("/importar", "Carga Masiva"), ("/compras/", "Órdenes de Compra"),
    ("/finanzas/cxc", "Cuentas por Cobrar"), ("/finanzas/cxp", "Cuentas por Pagar"),
    ("/finanzas/pagos", "Historial de Pagos"), ("/contactos", "Contactos"),
    ("/categorias", "Categorías"), ("/atributos", "Atributos"),
    ("/bcv/historial", "Historial de Tasas"), ("/configuracion/listas-precios", "Reglas de Listas de Precios"),
    ("/configuracion/marca", "Identidad Corporativa"), ("/configuracion/modulos", "Módulos y Funciones"),
    ("/usuarios", "Usuarios"), ("/notificaciones", "Notificaciones"),
]
FIGURAS_ROL = [
    ("admin_menu_configuracion", "Figura: Menú Configuración visto por el Administrador / Super Admin (8 opciones)"),
    ("supervisor_menu_configuracion", "Figura: Menú Configuración visto por el Supervisor (sin Identidad, Listas, Módulos ni Usuarios)"),
    ("supervisor_menu_inventario", "Figura: Menú Inventario del Supervisor (Productos, Lista de Precios, Movimientos, Carga Masiva)"),
    ("cajero_menu_ventas", "Figura: Barra de navegación del Cajero: solo el menú Ventas"),
    ("cajero_acceso_denegado", "Figura: Mensaje 'Acceso Denegado' cuando un Cajero intenta abrir /usuarios"),
]


def agregar_seccion_roles(doc, carpeta, ruta_accesos):
    """Inserta '2.4 Menús y opciones según el nivel de acceso' antes del Capítulo 3."""
    accesos = json.load(open(ruta_accesos, encoding="utf-8"))
    body = doc.element.body
    ps = list(body.iter(qn("w:p")))
    cap3 = next(p for p in ps if texto(p).strip().startswith("Capítulo 3:"))
    sub = next(p for p in ps if texto(p).strip().startswith("2.3"))
    cuerpo = next(p for p in ps[ps.index(sub) + 1:] if texto(p).strip())
    img_ref, cap_ref = parrafos_figura(body)[2]

    def parrafo(t, base):
        q = copy.deepcopy(base)
        poner_texto(q, t)
        return q

    nuevos = [parrafo("2.4 Menús y Opciones según el Nivel de Acceso", sub),
              parrafo("Al iniciar sesión, la barra superior muestra solo los menús que corresponden al rol del "
                      "usuario. Las capturas y la tabla siguientes se obtuvieron iniciando sesión con un usuario "
                      "de cada rol en el entorno de pruebas. Si un usuario escribe a mano la dirección de una "
                      "pantalla no permitida, el sistema lo devuelve al Panel principal con el mensaje "
                      "'Acceso Denegado'.", cuerpo)]

    # Tabla de menús por rol
    t = doc.add_table(rows=1, cols=4)
    t.style = "Table Grid"
    for i, h in enumerate(["Menú", "Super Admin / Administrador", "Supervisor", "Cajero"]):
        t.rows[0].cells[i].text = h
        t.rows[0].cells[i].paragraphs[0].runs[0].bold = True
    for menu in accesos["admin"]["menu"]:
        fila = t.add_row().cells
        fila[0].text = menu
        for i, rol in enumerate(["admin", "supervisor", "cajero"], start=1):
            fila[i].text = ", ".join(accesos[rol]["menu"].get(menu, [])) or "— (no visible)"
    nuevos.append(parrafo("Tabla 2.4.1: Opciones visibles en la barra de navegación por rol.", cap_ref))
    tabla_menu = t._tbl
    t2 = doc.add_table(rows=1, cols=4)
    t2.style = "Table Grid"
    for i, h in enumerate(["Pantalla", "Admin", "Supervisor", "Cajero"]):
        t2.rows[0].cells[i].text = h
        t2.rows[0].cells[i].paragraphs[0].runs[0].bold = True
    for url, nombre in PANTALLAS_ROL:
        fila = t2.add_row().cells
        fila[0].text = f"{nombre} ({url})"
        for i, rol in enumerate(["admin", "supervisor", "cajero"], start=1):
            fila[i].text = "Sí" if accesos[rol]["acceso"].get(url) == "SI" else "No"
    tabla_acc = t2._tbl

    # Insertar: titulo, intro, tabla menu, caption, intro tabla 2, tabla acceso, nota, figuras
    ancla = cap3
    for el in nuevos[:2]:
        ancla.addprevious(el)
    cap3.addprevious(tabla_menu)
    cap3.addprevious(nuevos[2])
    cap3.addprevious(parrafo("Acceso a cada pantalla (verificado abriendo la dirección con cada rol):", cuerpo))
    cap3.addprevious(tabla_acc)
    cap3.addprevious(parrafo("Tabla 2.4.2: Pantallas a las que puede entrar cada rol.", cap_ref))
    cap3.addprevious(parrafo(
        "Nota: el Cajero solo ve el menú Ventas, pero puede consultar Productos, Lista de Precios, Contactos "
        "e Historial de Tasas desde los botones del Punto de Venta o escribiendo la dirección; no puede crear "
        "ni modificar productos, compras, finanzas ni configuración.", cuerpo))
    for nombre, pie in FIGURAS_ROL:
        ruta = os.path.join(carpeta, nombre + ".png")
        img = copy.deepcopy(img_ref)
        rid, _ = doc.part.get_or_add_image(ruta)
        img.find(".//" + qn("a:blip")).set(qn("r:embed"), rid)
        inline = img.find(".//" + qn("wp:inline"))
        ext = inline.find(qn("wp:extent"))
        w, h = Image.open(ruta).size
        cy = int(int(ext.get("cx")) * h / w)
        ext.set("cy", str(cy))
        for e in inline.iter(qn("a:ext")):
            e.set("cy", str(cy))
        inline.find(qn("wp:docPr")).set("id", str(5000 + FIGURAS_ROL.index((nombre, pie))))
        cap3.addprevious(img)
        cap3.addprevious(parrafo(pie, cap_ref))

    # Índice del manual
    for p in ps:
        tx = texto(p)
        if tx.strip().startswith("▪") and "Capítulo 2:" in tx:
            poner_texto(p, tx.replace("Edición)", "Edición y Menús por Rol)"))


REPORTE_VENTAS = {
    "titulo": "5.1 Reporte de Ventas (PDF y Excel)",
    "intro": ("Desde Ventas → Historial de Ventas (/ventas/historial) se genera el reporte de ventas de un período. "
              "Los totales del período en USD y Bs se recalculan con los filtros aplicados y el reporte exporta "
              "exactamente las ventas que se ven en pantalla."),
    "pasos": [
        "1. Abra Ventas → Historial de Ventas.",
        "2. Indique la Fecha Inicio y la Fecha Fin del período (opcionalmente un cliente/referencia o un estado).",
        "3. Pulse el botón morado (filtro) para ver los resultados y los totales del período.",
        "4. Pulse el botón verde para descargar el reporte en Excel (.xlsx) o el rojo para descargarlo en PDF.",
        "5. El archivo se descarga con el nombre historial_ventas_<fecha>_<hora> y no queda guardado en el servidor.",
    ],
    "figuras": [
        ("56_reporte_ventas_filtros", "Figura 5.5: Filtros del período y botones Filtrar, Exportar a Excel y Exportar a PDF (totales aún sin filtrar)", None),
        ("57_historial_filtrado", "Figura 5.6: Historial filtrado del 01/09/2026 al 11/11/2026: 35 ventas por $6.202,65 (Bs. 5.144.088,47)", None),
        ("58_reporte_ventas_pdf", "Figura 5.7: Primera página del Reporte Histórico de Ventas en PDF", 0.62),
        ("59_reporte_ventas_excel", "Figura 5.8: Reporte de ventas exportado a Excel (columnas: ticket, fecha, cliente, identificación, vendedor, totales, tasa y estado)", 0.75),
    ],
}


def agregar_reporte_ventas(doc, carpeta):
    """Inserta la sección de reporte de ventas antes del Capítulo 6."""
    body = doc.element.body
    ps = list(body.iter(qn("w:p")))
    cap6 = next(p for p in ps if texto(p).strip().startswith("Capítulo 6:"))
    sub = next(p for p in ps if texto(p).strip().startswith("2.3"))
    cuerpo = next(p for p in ps[ps.index(sub) + 1:] if texto(p).strip())
    img_ref, cap_ref = parrafos_figura(body)[2]

    def parrafo(t, base):
        q = copy.deepcopy(base)
        poner_texto(q, t)
        return q

    for el in [parrafo(REPORTE_VENTAS["titulo"], sub), parrafo(REPORTE_VENTAS["intro"], cuerpo)] + \
            [parrafo(t, cuerpo) for t in REPORTE_VENTAS["pasos"]]:
        cap6.addprevious(el)
    for n, (nombre, pie, escala) in enumerate(REPORTE_VENTAS["figuras"]):
        ruta = os.path.join(carpeta, nombre + ".png")
        img = copy.deepcopy(img_ref)
        rid, _ = doc.part.get_or_add_image(ruta)
        img.find(".//" + qn("a:blip")).set(qn("r:embed"), rid)
        inline = img.find(".//" + qn("wp:inline"))
        ext = inline.find(qn("wp:extent"))
        cx = int(int(ext.get("cx")) * (escala or 1))
        w, h = Image.open(ruta).size
        cy = int(cx * h / w)
        ext.set("cx", str(cx))
        ext.set("cy", str(cy))
        for e in inline.iter(qn("a:ext")):
            e.set("cx", str(cx))
            e.set("cy", str(cy))
        inline.find(qn("wp:docPr")).set("id", str(5600 + n))
        cap6.addprevious(img)
        cap6.addprevious(parrafo(pie, cap_ref))
    for p in ps:
        tx = texto(p)
        if tx.strip().startswith("▪") and "Capítulo 5:" in tx:
            poner_texto(p, tx.replace("y Comprobantes", ", Comprobantes y Reporte de Ventas"))


def insertar_portada(doc, ruta_portada, titulo_buscar, materia, titulo):
    port = docx.Document(ruta_portada)
    pbody = port.element.body
    elementos = [copy.deepcopy(e) for e in pbody if e.tag != qn("w:sectPr")]
    sect = copy.deepcopy(pbody.find(qn("w:sectPr")))
    for hdr in sect.findall(qn("w:headerReference")) + sect.findall(qn("w:footerReference")):
        sect.remove(hdr)

    # imágenes de la portada -> nuevas relaciones en el manual
    for el in elementos:
        for blip in el.iter(qn("a:blip")):
            old = blip.get(qn("r:embed"))
            img_part = port.part.related_parts[old]
            import io
            rid, _ = doc.part.get_or_add_image(io.BytesIO(img_part.blob))
            blip.set(qn("r:embed"), rid)
        for dp in el.iter(qn("wp:docPr")):
            dp.set("id", str(9000 + int(dp.get("id", "1"))))

    # espaciado por defecto de la portada (after=200, line=276) explícito
    for el in elementos:
        if el.tag != qn("w:p"):
            continue
        ppr = el.find(qn("w:pPr"))
        if ppr is None:
            ppr = el.makeelement(qn("w:pPr"), {})
            el.insert(0, ppr)
        sp = ppr.find(qn("w:spacing"))
        if sp is None:
            sp = ppr.makeelement(qn("w:spacing"), {})
            ppr.append(sp)
        for clave, valor in (("w:after", "200"), ("w:before", "0"),
                             ("w:line", "276"), ("w:lineRule", "auto")):
            if sp.get(qn(clave)) is None:
                sp.set(qn(clave), valor)

    # título
    parrafos = [e for e in elementos if e.tag == qn("w:p")]
    i_tit = next(i for i, p in enumerate(parrafos) if titulo_buscar in texto(p))

    def centrar(p, nuevo, tam=None):
        poner_texto(p, nuevo)
        ppr = p.find(qn("w:pPr"))
        jc = ppr.find(qn("w:jc"))
        if jc is None:
            jc = ppr.makeelement(qn("w:jc"), {})
            ppr.append(jc)
        jc.set(qn("w:val"), "center")
        if tam:
            for r in p.iter(qn("w:r")):
                for sz in r.iter(qn("w:sz")):
                    sz.set(qn("w:val"), str(tam))

    centrar(parrafos[i_tit], materia, 28)
    siguiente = parrafos[i_tit + 1]
    if not texto(siguiente).strip():
        # clonar el párrafo del título para heredar fuente y negrita
        nuevo = copy.deepcopy(parrafos[i_tit])
        elementos[elementos.index(siguiente)] = nuevo
        centrar(nuevo, titulo, 32)

    # el último párrafo de la portada lleva el sectPr (fin de sección 1)
    ultimo = [e for e in elementos if e.tag == qn("w:p")][-1]
    ppr = ultimo.find(qn("w:pPr"))
    if ppr is None:
        ppr = ultimo.makeelement(qn("w:pPr"), {})
        ultimo.insert(0, ppr)
    ppr.append(sect)

    body = doc.element.body
    primero = body[0]
    for el in elementos:
        primero.addprevious(el)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manual", required=True)
    ap.add_argument("--portada", required=True)
    ap.add_argument("--capturas", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--accesos", default=None, help="JSON de menús y accesos por rol (opcional)")
    ap.add_argument("--titulo-buscar", default="Cableado de Redes")
    ap.add_argument("--materia", default="Sistemas Operativos:")
    ap.add_argument("--titulo", default="Manual de Usuario del Sistema SummanPOS")
    a = ap.parse_args()

    doc = docx.Document(a.manual)
    if any("Sistemas Operativos" in texto(p) for p in list(doc.element.body.iter(qn("w:p")))[:40]):
        sys.exit("El manual ya tiene la portada insertada; usa el manual original como entrada.")
    reemplazar_capturas(doc, a.capturas)
    agregar_secciones(doc, a.capturas)
    if a.accesos:
        agregar_seccion_roles(doc, a.capturas, a.accesos)
    if os.path.exists(os.path.join(a.capturas, "58_reporte_ventas_pdf.png")):
        agregar_reporte_ventas(doc, a.capturas)
    insertar_portada(doc, a.portada, a.titulo_buscar, a.materia, a.titulo)
    doc.core_properties.title = a.titulo
    doc.save(a.salida)
    print("OK ->", a.salida)


if __name__ == "__main__":
    main()
