# Actualizar el Manual de Usuario (.docx) de SummanPOS

**Objetivo:** regenerar `docs/manual_usuario/Manual_Usuario_SummanPOS.docx` (y su PDF) con capturas frescas del sistema y, si se pide, una portada institucional con título editado.
**Cuándo usarla:** el usuario pide "actualizar el manual" entregando el `.docx` (no un Claude Doc). Para el manual como Claude Doc, usar la skill `manual-usuario-summanpos`.

## Entradas
- Manual base: el `.docx` **original sin portada** (el script se niega a procesar uno que ya la tenga).
- Portada opcional (`.docx`), p.ej. la del IUJO; texto del título a reemplazar (`--titulo-buscar`), materia (`--materia`) y título (`--titulo`).
- URL del sistema (dev: `https://dev-mini-erp.summantech.com`) y credenciales de administrador dadas por el usuario en el chat o en `.env` — nunca escritas en scripts.

## Herramientas
- Playwright MCP (`browser_run_code_unsafe` para capturar en lote, viewport 1650x1050).
- `agents_scripts/actualizar_manual_docx.py` (python-docx + Pillow).
- Word (COM) para exportar PDF; PyMuPDF para renderizar páginas y revisarlas.

## Pasos
1. Iniciar sesión con Playwright y capturar cada pantalla a `.tmp/manual_v2/<nombre>.png` (nombres = lista `ORDEN_CAPTURAS` del script). Modales: abrirlos y **nunca** pulsar Guardar/Confirmar; datos de ejemplo ficticios.
2. Copiar las capturas a `docs/manual_usuario/screenshots/`.
3. Respaldar el `.docx` original en `.tmp/` y ejecutar:
   ```bash
   python agents_scripts/actualizar_manual_docx.py --manual .tmp/manual_v2/Manual_original_backup.docx --portada <portada.docx> --capturas docs/manual_usuario/screenshots --salida .tmp/manual_v2/Manual_nuevo.docx
   ```
4. Exportar a PDF con Word COM (`SaveAs2(..., 17)`), revisar portada y páginas con imágenes, y copiar ambos a `docs/manual_usuario/`.

## Salidas
- `docs/manual_usuario/Manual_Usuario_SummanPOS.docx` y `.pdf`; capturas en `docs/manual_usuario/screenshots/`.

## Casos extremos y errores conocidos
- Si el número de imágenes del manual cambia, el script aborta: ajustar `ORDEN_CAPTURAS`.
- `/dropshipping` devuelve 500 cuando el módulo está desactivado en Configuración → Módulos y Funciones; se conservan sus capturas anteriores (entradas `None`).
- Un script llamado `inspect.py` rompe la importación de lxml/python-docx (choca con el módulo estándar `inspect`).

## Historial de aprendizajes
- 2026-11-11 — El manual original reutilizaba la imagen del landing en el Dashboard y la del POS en el modal de cobro; el script crea relaciones nuevas por imagen para evitarlo.
