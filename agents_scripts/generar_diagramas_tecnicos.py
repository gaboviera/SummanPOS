"""Genera las páginas HTML (Mermaid) de los diagramas del Manual Técnico.

Lee el JSON de extraer_metadatos_tecnicos.py y escribe:
- arquitectura.html: cliente / servidor Flask / PostgreSQL / servicios externos.
- der.html: diagrama entidad-relación (columnas PK/FK) derivado de los modelos.
Luego se capturan a PNG con Playwright (elemento #diagrama).

Uso:
    python agents_scripts/generar_diagramas_tecnicos.py --metadatos .tmp/manual_tecnico/metadatos.json --salida .tmp/manual_tecnico
"""
import argparse
import json
import os

PLANTILLA = """<!doctype html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<style>body{{margin:0;background:#fff;font-family:Segoe UI,Arial}} #diagrama{{display:inline-block;padding:24px}}</style>
</head><body><div id="diagrama"><pre class="mermaid">
{codigo}
</pre></div>
<script>mermaid.initialize({{startOnLoad:true, theme:'base', themeVariables:{{primaryColor:'#EFE8FA',primaryBorderColor:'#4B2C7F',primaryTextColor:'#261640',lineColor:'#4B2C7F',fontSize:'15px'}}, er:{{useMaxWidth:false}}, flowchart:{{useMaxWidth:false}}, sequence:{{useMaxWidth:false, wrap:true, width:220}}}});</script>
</body></html>"""

INVENTARIO = {"productos", "categorias", "atributos", "valores_atributos", "productos_valores",
              "listas_precios", "producto_precios", "inventario", "transacciones", "proveedores",
              "productos_proveedores", "contactos"}
OPERACIONES = {"contactos", "usuarios", "roles", "guias_despacho", "pagos_cxc", "ordenes_compra",
               "detalle_orden_compra", "pagos_cxp", "ordenes_dropshipping", "detalle_dropshipping",
               "pagos_dropshipping", "notificaciones", "productos", "listas_precios"}

ARQUITECTURA = """flowchart TB
  subgraph C["Capa Cliente (Navegador)"]
    U["Usuario: Admin / Supervisor / Cajero"]
    FE["HTML Jinja2 + Bootstrap 5.3<br/>JavaScript, Tom-Select, SweetAlert2, Chart.js"]
    U --> FE
  end
  subgraph S["Servidor (VPS Linux + Docker)"]
    RP["Proxy inverso Caddy<br/>HTTPS / dominio"]
    subgraph APP["Contenedor inventario_app (Python 3.14)"]
      G["Gunicorn<br/>3 workers x 2 hilos :5000"]
      F["Flask 3.1 - create_app()"]
      BP["Blueprints / Controladores<br/>routes/*_routes.py"]
      SV["Capa de Servicios<br/>services/*_service.py"]
      M["Modelos ORM SQLAlchemy 2.0<br/>models.py"]
      SCH["APScheduler<br/>BCV 8:00 - USDT c/4h - limpieza 2:00"]
      G --> F --> BP --> SV --> M
      F --> SCH
    end
    VOL[("Volumen Docker<br/>static/uploads")]
    RP --> G
    BP --> VOL
  end
  subgraph D["Capa de Datos"]
    PG[("PostgreSQL<br/>flask_inventario_db")]
    MIG["Alembic / Flask-Migrate<br/>migrations/versions"]
  end
  subgraph EXT["Servicios Externos"]
    BCV["Banco Central de Venezuela<br/>tasa USD y EUR"]
    BIN["Binance P2P<br/>tasa USDT"]
    GCS["Google Cloud Storage<br/>respaldos .sql.gz"]
  end
  FE -- "HTTPS (GET/POST, fetch JSON)" --> RP
  M -- "psycopg2 / SQL" --> PG
  MIG -. "flask db upgrade" .-> PG
  SCH -- "requests + BeautifulSoup" --> BCV
  SCH -- "requests (API)" --> BIN
  PG -. "pg_dump (GitHub Actions)" .-> GCS
"""


SEGUNDO_PLANO = """sequenceDiagram
  autonumber
  actor U as Usuario
  participant W as Worker Gunicorn (hilo de la petición)
  participant H as Hilo en segundo plano (threading.Thread)
  participant DB as PostgreSQL
  participant FS as Disco: static/uploads
  U->>W: GET /descargar-pdf
  W->>H: Thread(run_pdf_generation).start()
  W-->>U: 302 a /productos + aviso: se está generando
  Note over U,W: El usuario sigue trabajando y la petición ya terminó
  H->>DB: Consulta productos, categorías y tasa BCV
  H->>H: Renderiza plantilla y genera PDF (xhtml2pdf) - uso de CPU
  H->>FS: Escribe Reporte_Inventario_FECHA_UUID.pdf
  H->>DB: INSERT notificacion (enlace /descargas/ARCHIVO)
  U->>W: Abre la campana o /notificaciones
  W-->>U: Enlace Descargar PDF
  U->>W: GET /descargas/ARCHIVO
  W->>FS: send_from_directory()
  W-->>U: Archivo PDF
  Note over FS: APScheduler 2:00 a.m. borra PDFs con más de RETENCION_PDF_DIAS
"""


def mermaid_tipo(t: str) -> str:
    t = t.split("(")[0].lower()
    return {"varchar": "string", "numeric": "decimal", "integer": "int", "boolean": "bool",
            "datetime": "datetime", "date": "date", "text": "text"}.get(t, t)


def generar_der(tablas: list, filtro: set | None = None, completo: bool = False) -> str:
    lineas = ["erDiagram"]
    relaciones = []
    if filtro:
        tablas = [t for t in tablas if t["tabla"] in filtro]
    for t in tablas:
        lineas.append(f"  {t['tabla']} {{")
        for c in t["columnas"]:
            claves = []
            if "PK" in c["restricciones"]:
                claves.append("PK")
            fks = [r for r in c["restricciones"] if r.startswith("FK")]
            if fks:
                claves.append("FK")
                destino = fks[0].split("→")[1].strip().split(".")[0]
                if not filtro or destino in filtro:
                    relaciones.append((destino, t["tabla"], c["nombre"]))
            if completo or claves or c["nombre"] in ("nombre", "referencia", "username", "valor", "clave", "tasa"):
                marca = (" " + ",".join(claves)) if claves else ""
                lineas.append(f"    {mermaid_tipo(c['tipo'])} {c['nombre']}{marca}")
        lineas.append("  }")
    for destino, origen, col in relaciones:
        lineas.append(f'  {destino} ||--o{{ {origen} : "{col}"')
    return "\n".join(lineas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadatos", required=True)
    ap.add_argument("--salida", required=True)
    a = ap.parse_args()
    datos = json.load(open(a.metadatos, encoding="utf-8"))
    os.makedirs(a.salida, exist_ok=True)
    diagramas = (
        ("arquitectura", ARQUITECTURA),
        ("segundo_plano", SEGUNDO_PLANO),
        ("der", generar_der(datos["tablas"])),
        ("der_inventario", generar_der(datos["tablas"], INVENTARIO, completo=True)),
        ("der_operaciones", generar_der(datos["tablas"], OPERACIONES)),
    )
    for nombre, codigo in diagramas:
        ruta = os.path.join(a.salida, nombre + ".html")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(PLANTILLA.format(codigo=codigo))
        print("OK", ruta)


if __name__ == "__main__":
    main()
