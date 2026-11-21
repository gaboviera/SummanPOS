# Desplegar SummanPOS

**Objetivo:** desplegar, reiniciar o destruir SummanPOS (`flask_iventario/`) en el entorno de la rama elegida mediante el workflow manual `deploy.yml`, con respaldo previo y migraciones aplicadas.
**Cuándo usarla:** cada vez que haya que publicar código nuevo en `dev`, `uat` o `prd`, reiniciar la app sin cambios de código, o bajar un entorno.

## Entradas
- **Rama** sobre la que se lanza el workflow: define el entorno (`main` → `prd`; cualquier otra → carpeta homónima). Los cambios ya deben estar pusheados a esa rama (ver `commit_y_push.md`).
- Inputs de `workflow_dispatch` de `.github/workflows/deploy.yml`:
  - `action`: `deploy` (por defecto) | `restart` | `destroy`.
  - `hacer_backup` (booleano, por defecto `true`): respalda la base antes de migrar. Solo tiene sentido desmarcarlo en `dev`.
- Este workflow **no** tiene input `provider`: corre siempre en el runner `[self-hosted, prd]`.
- Configuración del GitHub Environment (solo por nombre):
  - Variables: `DOMAIN_NAME`, `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `GCP_WIF_PROVIDER`, `GCP_SERVICE_ACCOUNT`.
  - Secrets: `PGPASSWORD`, `DOCKER_HUB_USERNAME`, `DOCKER_HUB_PASSWORD` (solo se usan en `main`), `GCP_BUCKET_NAME`.

## Herramientas
- `.github/workflows/deploy.yml` — el despliegue en sí.
- `.github/actions/backup-db/` — composite action: `pg_dump` desde un contenedor efímero en `<env>_shared_net` y subida del `.sql.gz` a GCS por Workload Identity Federation.
- `flask_iventario/docker-compose.yml` — servicio `inventario_app`.
- Detalle completo del workflow: [`../README.md`](../README.md), sección "Workflows de GitHub Actions" → `deploy.yml`.

## Pasos
1. Confirma que `check_migrations.yml` pasó en verde para el último push de la rama (si tocaste modelos, la migración debe estar en el commit; ver `crear_y_aplicar_migraciones.md`).
2. En GitHub → **Actions** → "Deploy SummanPOS" → **Run workflow**, elige la rama y el `action`. Deja `hacer_backup` activado salvo en `dev`.
3. El workflow ejecuta, en orden:
   1. `rsync -a --delete` del repo a `/opt/deploy/<env>/SummanPOS/` (excluye `.git` y `flask_iventario/.env`).
   2. Si `action=destroy`: valida permisos (`AUTHORIZED_USERS`).
   3. Genera `flask_iventario/.env` a partir de variables y secrets del Environment.
   4. Crea la red `<env>_shared_net` si no existe.
   5. `destroy` → `docker-compose down`; `restart` → `docker-compose restart`; `deploy` → en `main` login a Docker Hub + `build`/`push`/`pull`/`up -d --remove-orphans`; en otras ramas `up --build -d --remove-orphans`.
   6. (`deploy` + `hacer_backup`) respaldo con `backup-db`.
   7. (`deploy`) `flask db upgrade` dentro de `inventario_app`, con autocorrección del caso `Can't locate revision` vía `flask db stamp --purge head`, y luego `flask db check`.
   8. (`deploy`) `flask seed-inicial` (roles y admin).
   9. (`deploy`/`restart`) health-check: hasta 10 intentos contra `/login` dentro del contenedor.
4. Revisa que el run termine en verde. Si falla el health-check, el propio job imprime `docker-compose logs --tail 50 inventario_app`.
5. Si el deploy cambió el nombre de un contenedor, actualiza `infra-caddy/Caddyfile.*` en el mismo cambio o el subdominio devolverá 502.

## Salidas
- Contenedor `inventario_app` corriendo en `/opt/deploy/<env>/SummanPOS/flask_iventario`, conectado a `<env>_shared_net`.
- Base migrada a `head` y esquema verificado con `flask db check`.
- Backup `.sql.gz` en el bucket de GCS (si `hacer_backup`).
- En `prd`, imagen publicada en Docker Hub.

## Casos extremos y errores conocidos
- **Ventana de incompatibilidad:** `up -d` levanta el código nuevo *antes* del `upgrade`; las migraciones deben ser compatibles hacia atrás (patrón expand/contract, ver [`../README.md`](../README.md) "Las migraciones deben ser compatibles hacia atrás").
- **`Can't locate revision`:** el workflow lo repara solo con `stamp --purge head`. Cualquier otro fallo del `upgrade` aborta el deploy a propósito; no sellar a mano sin entender la causa.
- **`flask db check` falla:** el esquema real no coincide con los modelos (típico tras un stamp sobre una base desalineada). Revisar con `db_migrations.yml` (`action=current`) antes de reintentar.
- **Backup de menos de 1 KB:** `backup-db` aborta el job porque el `pg_dump` falló; no desmarcar `hacer_backup` para "saltarse" el error.
- **Concurrencia:** comparte el grupo `summanpos-<rama>` con `db_migrations.yml`; un run queda en espera si el otro está en curso.
- **`destroy` sin control real:** `AUTHORIZED_USERS` está vacío, así que cualquiera con permiso sobre Actions puede destruir el entorno. Confirmar con el usuario antes de lanzar `destroy`.
- **Runner fijo:** `runs-on: [self-hosted, prd]` para todas las ramas; no sigue el patrón `<provider>-<env>` del resto de la plataforma.

## Historial de aprendizajes
- 2026-09-25 — Directiva creada a partir de `.github/workflows/deploy.yml`, `.github/actions/backup-db/action.yml` y `README.md`.
