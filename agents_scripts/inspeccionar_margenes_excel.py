"""
Diagnostico: genera el Excel del recibo (via generar_recibo_excel, sin pasar
por HTTP/login) para una venta real de la BD y vuelca los page_margins que
quedan grabados en el .xlsx, para verificar en centimetros lo que Excel
aplicara realmente al imprimir.

Uso:
    python agents_scripts/inspeccionar_margenes_excel.py [referencia]

Si no se pasa referencia, usa la guia de despacho mas reciente.
No requiere sesion ni credenciales: se ejecuta dentro del contexto de la app
Flask directamente contra el ORM, igual que cualquier script de agents_scripts/.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'flask_iventario'))

from app import create_app
from extensions import db
from models import GuiaDespacho, Transacciones
from services.ventas_service import generar_recibo_excel

CM_POR_PULGADA = 2.54

app = create_app()

with app.app_context():
    referencia = sys.argv[1] if len(sys.argv) > 1 else None

    if referencia:
        guia = GuiaDespacho.query.filter_by(referencia=referencia).first()
    else:
        guia = GuiaDespacho.query.order_by(GuiaDespacho.id.desc()).first()

    if not guia:
        print("No se encontro ninguna guia de despacho en la BD.")
        sys.exit(1)

    transacciones = Transacciones.query.filter_by(referencia=guia.referencia).all()
    print("Referencia:", guia.referencia, "| items:", len(transacciones))

    for formato in ("con-encabezado", "sin-encabezado"):
        salida = generar_recibo_excel(
            guia, transacciones,
            es_devolucion=False, es_ajuste=False,
            vendedor_telefono="", vendedor_display=guia.vendedor_nombre,
            formato=formato,
        )
        ruta = "/tmp/recibo_%s.xlsx" % formato.replace("-", "_")
        with open(ruta, "wb") as f:
            f.write(salida.getvalue())

        import openpyxl
        wb = openpyxl.load_workbook(ruta)
        print("\n=== formato:", formato, "===")
        for hoja in wb.worksheets:
            m = hoja.page_margins
            print(
                "  hoja=%-16s top=%.4fcm bottom=%.4fcm left=%.4fcm right=%.4fcm header=%.4fcm footer=%.4fcm"
                % (
                    hoja.title,
                    m.top * CM_POR_PULGADA,
                    m.bottom * CM_POR_PULGADA,
                    m.left * CM_POR_PULGADA,
                    m.right * CM_POR_PULGADA,
                    (m.header or 0) * CM_POR_PULGADA,
                    (m.footer or 0) * CM_POR_PULGADA,
                )
            )
        print("  archivo guardado en:", ruta)
