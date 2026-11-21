# Catálogo de Scripts de Diagnóstico y Utilidades (`agents_scripts/`)

Este directorio alberga los scripts auxiliares creados por agentes de IA y desarrolladores para diagnósticos, pruebas de base de datos, consultas a la VPS y migraciones de SummanPOS.

> **Regla de Operación:**
> 1. Todo script nuevo en esta carpeta **debe** incluir un docstring de cabecera con su propósito y comando de ejecución.
> 2. Cada nuevo script **debe ser registrado en este archivo (`README.md`)**.
> 3. Las credenciales deben consumirse vía variables de entorno (`os.environ`). Nunca hardcodear contraseñas de producción.

---

## Scripts Registrados

| Script | Propósito / Descripción | Comando de Ejecución | Estado |
| :--- | :--- | :--- | :---: |
| `check_docker.py` | Comprueba el estado y nombres de los contenedores Docker en la VPS | `python agents_scripts/check_docker.py` | Diagnóstico |
| `check_erp.py` | Comprueba contenedores del ERP en la VPS | `python agents_scripts/check_erp.py` | Diagnóstico |
| `check_logs.py` | Consulta las últimas 200 líneas de logs del contenedor `dev-summanpos_inventario_app_1` | `python agents_scripts/check_logs.py` | Diagnóstico |
| `check_logs_erp.py` | Consulta logs de servicios ERP en la VPS | `python agents_scripts/check_logs_erp.py` | Diagnóstico |
| `fetch_migration.py` | Descarga archivos de migración generados en el contenedor DEV vía SFTP | `python agents_scripts/fetch_migration.py` | Utilidad |
| `fix_migrations.py` | Ejecuta `flask db migrate` para generar revisiones de migración en la base de datos DEV | `python agents_scripts/fix_migrations.py` | Mantenimiento |
| `run_migrations.py` | Ejecuta `flask db upgrade` para aplicar migraciones pendientes en el contenedor DEV | `python agents_scripts/run_migrations.py` | Mantenimiento |
