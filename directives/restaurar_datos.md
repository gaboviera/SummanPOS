# Restaurar datos de SummanPOS desde GCS

**Objetivo:** restaurar la base de datos y/o el volumen de archivos subidos de SummanPOS en un entorno, a partir de un respaldo diario en Google Cloud Storage, mediante el workflow manual `restore.yml`.
**Cuándo usarla:** recuperación ante pérdida o corrupción de datos, o para bajar datos de un entorno a otro (p. ej. de `prd` a `dev`) para pruebas.

## Entradas
- Inputs de `workflow_dispatch` de `.github/workflows/restore.yml`:
  - `target_namespace`: `dev` | `uat` | `prd` — dónde se restaura (también elige el GitHub Environment).
  - `source_namespace`: `dev` | `uat` | `prd` — de qué entorno viene el backup.
  - `backup_date`: fecha del respaldo, formato `YYYY-MM-DD`.
  - `host_prefix`: prefijo del host con el que se nombraron los backups (tiene un valor por defecto en el workflow; confírmalo contra el nombre real del archivo en el bucket).
  - `restore_db` (booleano) y `db_restore_target`: `azure` | `docker`.
  - `restore_volume` (booleano).
- Configuración del Environment destino (solo por nombre): variables `GCP_WIF_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `GCP_BUCKET_NAME`, `PGHOST`, `PGUSER`; secret `PGPASSWORD`.

## Herramientas
- `.github/workflows/restore.yml` — orquesta tres jobs: detener, restaurar, arrancar.
- Workflow reutilizable `SummanTech/infra-templates/.github/workflows/restore-data.yml@main` — hace la restauración real (BD `flask_inventario_db`, volumen `inventario` → `<target>-summanpos_inventario_uploads`).
- Resumen oficial: [`../README.md`](../README.md), sección "`restore.yml` — Restauración de Datos".

## Pasos
1. Confirma con el usuario el entorno destino, el origen y la fecha. Si el destino es `prd`, pide confirmación explícita: sobrescribe datos de producción.
2. Verifica que el backup de esa fecha y prefijo existe en el bucket de GCS antes de lanzar el workflow.
3. `restore.yml` no invoca `backup-db` sobre el destino antes de sobrescribirlo. Si se quiere un punto de retorno del estado actual, confirma que existe un backup reciente del entorno destino en GCS antes de continuar.
4. Actions → "Restore SummanPOS Data" → **Run workflow** con los inputs acordados.
5. El workflow:
   1. `stop_containers`: valida permisos (`AUTHORIZED_USERS`) y detiene los contenedores de la app (prueba varios nombres con `|| true`).
   2. `restore`: llama a `restore-data.yml` con `db_backup_source: azure_db`, la BD `flask_inventario_db`, el contenedor `<target>-postgres_postgres_1` y el volumen destino.
   3. `start_containers`: vuelve a arrancar los contenedores.
6. Tras el run, comprueba la revisión de Alembic con `db_migrations.yml` (`action=current`). Si el backup viene de una revisión anterior, aplica `upgrade` (o un `deploy`) para alinear el esquema con el código de la rama.
7. Comprueba que la app responde (login) en el entorno destino.

## Salidas
- Base `flask_inventario_db` y/o volumen de uploads del entorno destino reemplazados por el contenido del backup.
- Contenedores de SummanPOS arrancados de nuevo.

## Casos extremos y errores conocidos
- **Sin control de acceso real:** `AUTHORIZED_USERS` está vacío; cualquiera con permiso sobre Actions puede sobrescribir datos. Nunca lanzar contra `prd` sin confirmación del usuario.
- **Nombres de contenedor heredados:** los pasos stop/start prueban `inventario_app`, `<target>-summanpos_inventario_app_1` y `flask_iventario_app_1`, todos con `|| true`: un nombre que no coincide no falla el job, y la app podría seguir corriendo durante la restauración. Revisar el log de `stop_containers`.
- **Sin grupo de concurrencia:** a diferencia de `deploy.yml` y `db_migrations.yml`, `restore.yml` no comparte el grupo `summanpos-<rama>`; evita lanzarlo mientras corre un deploy o una migración sobre el mismo entorno.
- **Esquema desfasado:** restaurar un backup antiguo deja la base en una revisión anterior al código desplegado; hay que migrar después (paso 6).
- **`GCP_BUCKET_NAME` como variable:** `restore.yml` lo lee de `vars`, mientras que `deploy.yml`/`db_migrations.yml` lo leen de `secrets`; el Environment debe tener ambos definidos o uno de los flujos quedará sin bucket.

## Historial de aprendizajes
- 2026-09-25 — Directiva creada a partir de `.github/workflows/restore.yml` y `README.md`.
