# Crear y aplicar migraciones de base de datos

**Objetivo:** generar en local la migración Alembic de cada cambio de modelos, hacerla pasar por PR y CI, y operarla en los entornos desplegados solo mediante `deploy.yml` o `db_migrations.yml`.
**Cuándo usarla:** siempre que se modifique un modelo SQLAlchemy de `flask_iventario/` (`models.py`), o cuando haya que consultar, aplicar, revertir o estampar la revisión de una base ya desplegada.

## Entradas
- Cambio en los modelos de `flask_iventario/`.
- Historial en `flask_iventario/migrations/versions/` (baseline `0001_baseline_esquema_completo.py` y siguientes).
- Para operar un entorno: rama objetivo y los inputs de `.github/workflows/db_migrations.yml`:
  - `action`: `current` | `upgrade` (por defecto) | `rollback` | `stamp`.
  - `rollback_target` (por defecto `-1`), solo para `rollback`.
  - `stamp_target` (por defecto `0001_baseline`), solo para `stamp`.
- Variables/secrets del Environment que usa el respaldo automático (por nombre): `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `GCP_WIF_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `PGPASSWORD`, `GCP_BUCKET_NAME`.

## Herramientas
- Flask-Migrate (`flask db migrate|upgrade|downgrade|current|stamp|check`), con `FLASK_APP=app.py`.
- `.github/workflows/check_migrations.yml` — CI automático en push/PR a `dev` y `main`.
- `.github/workflows/db_migrations.yml` — operaciones manuales dentro del contenedor `inventario_app` desplegado.
- `.github/workflows/deploy.yml` — aplica `upgrade` + `check` en cada deploy (ver `desplegar_summanpos.md`).
- Reglas completas: [`../README.md`](../README.md), secciones "`db_migrations.yml`", "REGLA DE MIGRACIONES DE BASE DE DATOS" y "Las migraciones deben ser compatibles hacia atrás".

## Pasos
**A. Generar la migración (local, nunca contra una base desplegada)**
1. Modifica el modelo respetando el patrón expand/contract: columnas nuevas `nullable=True` o con `server_default`; nada de renombrar, borrar ni cambiar tipos en la misma entrega que deja de usarlos.
2. Contra una base local, ejecuta en `flask_iventario/`: `flask db migrate -m "Descripción del cambio"`. (El CI usa `FLASK_APP=app.py` y `SKIP_DB_BOOTSTRAP=1`; reproduce esas variables si el arranque de la app interfiere.)
3. Revisa a mano el archivo generado en `migrations/versions/` (autogenerate no detecta todo; verifica `upgrade()` y `downgrade()`).
4. Aplica en local con `flask db upgrade` y prueba el `downgrade` si la migración debe ser reversible.
5. Incluye el archivo de migración en el mismo commit que el cambio de modelo (ver `commit_y_push.md`).

**B. Validación en CI**
6. `check_migrations.yml` corre solo: aplica el historial sobre Postgres limpio, ejecuta `flask db migrate -m "CI Check"` y **falla** si eso genera un archivo nuevo (modelo cambiado sin migración).

**C. Aplicar en un entorno**
7. Vía normal: lanzar `deploy.yml` con `action=deploy`; aplica `upgrade` y `flask db check` automáticamente.
8. Operación puntual sin redeploy: Actions → "DB Migrations SummanPOS" → rama del entorno → `action`:
   - `current` para ver la revisión (solo lectura, sin backup).
   - `upgrade` para aplicar pendientes.
   - `rollback` con `rollback_target` (id de revisión o `-1`).
   - `stamp` con `stamp_target` para marcar una base preexistente sin ejecutar DDL (usa `--purge`).
   Las tres últimas hacen backup previo automático con `backup-db`.

## Salidas
- Archivo nuevo en `flask_iventario/migrations/versions/` versionado junto al cambio de modelo.
- CI `check_migrations.yml` en verde.
- Base del entorno en la revisión esperada (`flask db current`) y respaldo en GCS antes de cada operación mutante.

## Casos extremos y errores conocidos
- **No existe acción `migrate` en `db_migrations.yml`, a propósito:** generaba migraciones contra la base viva y hacía push desde el runner, saltándose PR y CI.
- **`agents_scripts/fix_migrations.py` contradice esta regla:** ejecuta `flask db migrate` (con un mensaje fijo) y `upgrade` dentro del contenedor DEV por SSH. No usarlo para generar migraciones nuevas; lo mismo aplica a `fetch_migration.py`, que descarga un archivo de migración concreto y ya histórico.
- **`Multiple head revisions`:** apareció cuando el deploy copiaba con `cp` y sobrevivían migraciones borradas en el servidor; hoy `rsync --delete` lo evita. Si reaparece localmente, hay dos migraciones con el mismo `down_revision`: fusiónalas o re-encadénalas antes del PR.
- **`Can't locate revision` tras un squash:** `flask db stamp head` a secas falla igual; hay que usar `--purge` (Flask-Migrate >= 2.6).
- **`rollback` solo es seguro** si la migración se escribió pensando en revertirse; un `downgrade` puede borrar columnas con datos (por eso hay backup previo).
- **Concurrencia:** `db_migrations.yml` y `deploy.yml` comparten el grupo `summanpos-<rama>`; no se ejecutan a la vez.

## Historial de aprendizajes
- 2026-09-25 — Directiva creada a partir de `check_migrations.yml`, `db_migrations.yml`, `deploy.yml`, `README.md` y `agents_scripts/` (`fix_migrations.py`, `fetch_migration.py`, `run_migrations.py`).
