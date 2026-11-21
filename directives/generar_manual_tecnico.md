# Generar el Manual Técnico de SummanPOS

**Objetivo:** producir `docs/manual_tecnico/Manual_Tecnico_SummanPOS.docx` y su PDF, con portada institucional, a partir del código real de `flask_iventario/` (modelos, rutas, servicios).
**Cuándo usarla:** se pide crear o actualizar el manual técnico (p. ej. tras cambiar modelos o rutas).

## Entradas
- Código de `flask_iventario/` (models.py, routes/, services/, requirements.txt, Dockerfile).
- Portada `.docx` (la del IUJO; el párrafo "Cableado de Redes" se reemplaza por la materia y el título).

## Herramientas
- `agents_scripts/extraer_metadatos_tecnicos.py` → JSON con tablas (introspección SQLAlchemy) y rutas (análisis `ast`).
- `agents_scripts/generar_diagramas_tecnicos.py` → HTML Mermaid (arquitectura y DER); se capturan a PNG con Playwright MCP (`#diagrama`, `scale: device`).
- `agents_scripts/generar_manual_tecnico.py` → arma el `.docx` (reusa `insertar_portada` de `actualizar_manual_docx.py`).
- Word COM para actualizar el índice (`TablesOfContents(1).Update()`) y exportar PDF.

## Pasos
1. Venv aislado con las dependencias mínimas para importar `models.py`:
   ```bash
   python -m venv .tmp/venv_doc
   .tmp/venv_doc/Scripts/python -m pip install Flask==3.1.3 Flask-SQLAlchemy==3.1.1 Flask-Login==0.6.3 Flask-Bcrypt==1.0.1 Flask-Migrate==4.1.0
   ```
2. `.tmp/venv_doc/Scripts/python agents_scripts/extraer_metadatos_tecnicos.py --salida .tmp/manual_tecnico/metadatos.json`
3. `python agents_scripts/generar_diagramas_tecnicos.py --metadatos .tmp/manual_tecnico/metadatos.json --salida .tmp/manual_tecnico`, luego capturar cada HTML con Playwright y copiar los PNG a `docs/manual_tecnico/diagramas/`.
4. `python agents_scripts/generar_manual_tecnico.py --metadatos .tmp/manual_tecnico/metadatos.json --diagramas docs/manual_tecnico/diagramas --portada <portada.docx> --salida docs/manual_tecnico/Manual_Tecnico_SummanPOS.docx`
5. Abrir con Word COM, actualizar el índice, guardar y exportar a PDF; revisar páginas con PyMuPDF.

6. Medición de recursos (capítulo 10): con Docker Desktop abierto, red `manual_net`, contenedor `postgres:15` (`manual_pg`) y la imagen local (`manual_app`, puerto 5055) usando un env generado en `.tmp/manual_tecnico/local.env`; `flask db upgrade` + `flask seed-inicial` + productos sintéticos (`.tmp/manual_tecnico/datos_prueba.sql`). Luego `agents_scripts/medir_recursos_docker.py snapshot|muestreo` mientras se dispara `/descargar-pdf` con Playwright. Guardar `resumen.json`, CSV y gráfico en `docs/manual_tecnico/mediciones/`. Borrar contenedores, volumen y red al terminar.
7. Capturas de archivos en `docs/manual_tecnico/capturas/`; menús por rol para el manual de usuario con `agents_scripts/actualizar_manual_docx.py --accesos docs/manual_usuario/accesos_por_rol.json`.

## Salidas
- `docs/manual_tecnico/Manual_Tecnico_SummanPOS.docx`, `.pdf` y `diagramas/*.png`.

## Casos extremos y errores conocidos
- Las descripciones de columnas/tablas nuevas se agregan a mano en `DESC_TABLAS` / `DESC_ESPECIFICAS`; si faltan, salen como "—".
- Los blueprints protegidos con `before_request` se marcan "Autenticado"; solo `/` y `/login` son públicos.
- Mermaid dibuja el DER completo muy ancho: va en una sección horizontal; las vistas por área van en vertical.
- Nunca copiar la URL de `git remote` al documento: puede contener un token embebido.

- En Git Bash, `docker pull` falla con `docker-credential-desktop not found`: usar PowerShell o agregar `C:\Program Files\Docker\Docker\resources\bin` al PATH.
- SSH al VPS de producción (`metricas_recursos_vps.py`) puede ser bloqueado por la política de permisos; medir en Docker local o pedir al usuario que lo ejecute.
- Mermaid `sequenceDiagram`: no usar `<...>` ni `;` en los mensajes y fijar `sequence.useMaxWidth:false` o sale diminuto.

## Historial de aprendizajes
- 2026-11-11 — Medición local: 3 PDF simultáneos de 3000 productos saturan un núcleo ~2 min y elevan la RAM de 329 MB a 1,38 GB; el worker retiene ~1,15 GB después (recomendado `--max-requests`).
- 2026-11-11 — Directiva creada. Hallazgos documentados en el manual: SECRET_KEY no se inyecta en deploy.yml (se usa 'default_secret'), sin CSRFProtect global y redirección rota a 'inventario.index' en dropshipping.
