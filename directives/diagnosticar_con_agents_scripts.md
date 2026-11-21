# Diagnosticar SummanPOS con agents_scripts

**Objetivo:** inspeccionar el estado de SummanPOS (contenedores y logs en el VPS, o el render de recibos en local) con los scripts existentes de `agents_scripts/`, sin exponer credenciales ni modificar la base.
**Cuándo usarla:** la app no responde tras un deploy, hay errores 500, se necesita ver logs del contenedor DEV, o hay que depurar el formato del recibo (HTML/Excel) de una venta.

## Entradas
- Para scripts remotos (SSH con `paramiko`), variables de entorno: `VPS_HOST`, `VPS_USER` (por defecto `root`), `VPS_PASSWORD`. Se cargan desde el entorno local o un `.env` fuera del repo; nunca se escriben en el script ni en la conversación.
- Para scripts locales: entorno Python con las dependencias de `flask_iventario/requirements.txt` y acceso a una base local (la app se crea con `create_app()`).
- Referencia de una guía de despacho/venta (opcional en `inspeccionar_margenes_excel.py`, obligatoria en `renderizar_recibo_html.py`).

## Herramientas
Catálogo: [`../agents_scripts/README.md`](../agents_scripts/README.md).

| Script | Qué hace | Tipo |
| :--- | :--- | :--- |
| `check_docker.py` | Lista nombres de contenedores (`docker ps`) en el VPS | Solo lectura |
| `check_erp.py` | Igual que el anterior, con otra etiqueta de salida | Solo lectura |
| `check_logs.py` | Últimas 200 líneas de `dev-summanpos_inventario_app_1` | Solo lectura |
| `check_logs_erp.py` | Hoy es idéntico a `check_logs.py` (mismo contenedor) | Solo lectura |
| `run_migrations.py` | `flask db upgrade` en el contenedor DEV | **Modifica la BD** |
| `fix_migrations.py` | `flask db migrate` + `upgrade` en DEV | **Modifica la BD y genera archivos** |
| `fetch_migration.py` | Descarga por SFTP una migración concreta del contenedor DEV | Escribe en el repo |
| `inspeccionar_margenes_excel.py [referencia]` | Genera el Excel del recibo y vuelca sus `page_margins` | Local, solo lectura |
| `renderizar_recibo_html.py <referencia> <formato> <salida.html>` | Renderiza el HTML real del recibo con una sesión de prueba del usuario `admin` | Local, solo lectura de BD |

## Pasos
1. Antes de tocar el VPS, prefiere las vías sin SSH: el log del run de `deploy.yml` (el health-check ya vuelca `docker-compose logs --tail 50 inventario_app`) y `db_migrations.yml` con `action=current`.
2. Si hace falta el VPS, exporta `VPS_HOST`, `VPS_USER` y `VPS_PASSWORD` en la sesión (sin imprimirlos) y ejecuta desde la raíz del repo:
   - `python agents_scripts/check_docker.py` para confirmar qué contenedores existen y cómo se llaman.
   - `python agents_scripts/check_logs.py` para las últimas 200 líneas de la app en DEV.
3. Para otro entorno o contenedor, no edites el script existente a ciegas: crea uno parametrizado en `agents_scripts/` (docstring de cabecera + registro en su README) que reciba el nombre del contenedor por argumento.
4. Para depurar recibos en local:
   - `python agents_scripts/inspeccionar_margenes_excel.py [referencia]` → escribe `/tmp/recibo_con_encabezado.xlsx` y `/tmp/recibo_sin_encabezado.xlsx` e imprime márgenes en cm.
   - `python agents_scripts/renderizar_recibo_html.py <referencia> <formato> <salida.html>` → guarda el HTML de `/ventas/recibo/<referencia>?formato=<formato>`; úsalo con `.tmp/` como destino.
5. No ejecutes `run_migrations.py` ni `fix_migrations.py` como diagnóstico: modifican la base. Para migraciones usa `crear_y_aplicar_migraciones.md`.
6. Registra hallazgos no triviales en el "Historial de aprendizajes" de esta directiva.

## Salidas
- Listado de contenedores y logs impresos en consola.
- Archivos de diagnóstico de recibos (`.xlsx` en `/tmp/`, `.html` en la ruta indicada, preferentemente `.tmp/`).

## Casos extremos y errores conocidos
- **Nombres de contenedor fijos:** los scripts SSH apuntan a `dev-summanpos_inventario_app_1`; si el deploy cambió el nombre (el compose de la app usa el servicio `inventario_app`), fallarán sin error claro. Verifica primero con `check_docker.py`.
- **`check_logs_erp.py` y `check_erp.py` no miran el ERP:** su contenido es equivalente a `check_logs.py`/`check_docker.py`. No asumir que diagnostican otro servicio.
- **Sin `VPS_HOST`:** `paramiko` falla al conectar con un host `None`; los scripts no validan las variables antes de usarlas.
- **Scripts no registrados:** `inspeccionar_margenes_excel.py` y `renderizar_recibo_html.py` no figuran en `agents_scripts/README.md`.
- **`renderizar_recibo_html.py`** requiere que exista el usuario `admin` en la base local; termina con código 1 si no.
- **`/tmp/` en Windows:** las rutas `/tmp/...` de `inspeccionar_margenes_excel.py` asumen un entorno tipo Unix.

## Historial de aprendizajes
- 2026-09-25 — Directiva creada a partir del contenido de `agents_scripts/*.py` y `agents_scripts/README.md`.
