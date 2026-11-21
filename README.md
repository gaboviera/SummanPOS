# SummanPOS - API & Inventario

Este repositorio contiene el código fuente de SummanPOS, una aplicación basada en Flask para gestión de inventarios y punto de venta.

## Arquitectura de Despliegue (GitOps)

El despliegue de esta aplicación está automatizado mediante GitHub Actions siguiendo los más altos estándares de infraestructura:

- **Red Compartida Centralizada:** Los contenedores se conectan a `<env>_shared_net` (ej. `prd_shared_net`). Esto permite que la aplicación se comunique internamente con la base de datos central (`postgres`) y con el proxy inverso (`caddy`) de forma completamente segura y sin exponer puertos al exterior.
- **Ruta Estándar:** El código se despliega y ejecuta desde la ruta unificada `/opt/deploy/<env>/SummanPOS` en el servidor VPS, manteniendo la persistencia y orden de la infraestructura.
- **Entorno por rama:** La rama determina el entorno. `main` despliega en `prd`; cualquier otra rama despliega en una carpeta con su propio nombre (`dev`, `uat`).
- **Mantenimiento Automático (Mend Renovate):** Este repositorio está configurado con Renovate Bot para monitorear y proponer actualizaciones automáticamente sobre las dependencias, librerías y versiones de Docker utilizadas en el proyecto.

## Workflows de GitHub Actions

El repositorio tiene cuatro workflows en `.github/workflows/`. Solo uno se dispara solo; los otros tres se lanzan a mano desde la pestaña **Actions**.

| Workflow | Archivo | Disparo | Runner | Para qué sirve |
|---|---|---|---|---|
| CI - Verificación de Migraciones | `check_migrations.yml` | Automático: push y PR a `dev` / `main` | GitHub (`ubuntu-latest`) | Bloquea el cambio si tocaste un modelo y no subiste su migración |
| Deploy SummanPOS | `deploy.yml` | Manual | Self-hosted (VPS) | Despliega, reinicia o destruye el entorno de la rama |
| DB Migrations SummanPOS | `db_migrations.yml` | Manual | Self-hosted (VPS) | Opera Alembic contra la base ya desplegada, sin entrar por SSH |
| Restore SummanPOS Data | `restore.yml` | Manual | Self-hosted (VPS) | Restaura base de datos y/o volumen de archivos desde una copia en GCS |

Además hay una *composite action* compartida en `.github/actions/backup-db/`, que vuelca la base con `pg_dump` y sube el `.sql.gz` a Google Cloud Storage. La usan `deploy.yml` y `db_migrations.yml` para que ninguna operación que toque el esquema corra sin copia previa. Aborta si el volcado pesa menos de 1 KB, porque un `pg_dump` fallido deja igualmente un `.gz` válido pero vacío.

### 1. `check_migrations.yml` — Verificación de Migraciones

Es el único que corre solo, en cada push y cada pull request contra `dev` y `main`, y es la red de seguridad de la regla de migraciones descrita más abajo.

Levanta un PostgreSQL 15 desechable como *service container*, instala las dependencias en un virtualenv **fuera del repositorio** (para no ensuciar `git status`, del que depende la comprobación final) y entonces:

1. `flask db upgrade` — aplica las migraciones existentes sobre la base limpia. Si el historial de Alembic está roto, falla aquí.
2. `flask db migrate` — intenta autogenerar una migración nueva.
3. Comprueba con `git status` si ese paso creó un archivo en `migrations/versions/`. **Si lo creó, falla el workflow**: significa que los modelos cambiaron y nadie generó la migración correspondiente.

Usa `SKIP_DB_BOOTSTRAP=1` para que importar `app.py` no cree las tablas antes de que Alembic pueda hacerlo, lo que enmascararía el problema. Al terminar borra siempre los contenedores y el virtualenv, pase lo que pase.

### 2. `deploy.yml` — Deploy SummanPOS

Se ejecuta **a mano** desde Actions, sobre la rama que elijas. Tiene dos entradas:

- **`action`**: `deploy` (por defecto), `restart` o `destroy`.
- **`hacer_backup`**: respalda la base antes de migrar. **Activado por defecto**; desmarcarlo solo tiene sentido en `dev` y para ganar tiempo. No controla si se aplican las migraciones: eso ocurre siempre en un deploy.

Lo que hace, en orden:

1. Sincroniza el repositorio en `/opt/deploy/<env>/SummanPOS` con `rsync --delete`, excluyendo `.git` y el `.env`. Se usa rsync y no `cp` porque `cp` no borra: los archivos eliminados en git sobrevivían en el servidor. Eso provocó el error *"Multiple head revisions"* de Alembic con las migraciones, y el mismo problema afectaba en silencio a templates, rutas y estáticos.
2. Genera el `.env` en el servidor a partir de las *variables* y *secrets* del entorno de GitHub (`PGHOST`, `PGUSER`, `PGPASSWORD`, `DOMAIN_NAME`…). El `.env` nunca viaja en el repositorio.
3. Crea la red `<env>_shared_net` si no existe.
4. Según la acción: `docker-compose down` (destroy), `docker-compose restart` (restart) o el despliegue. En `main` hace login en Docker Hub, `build`, `push`, `pull` y `up -d`; en `dev` y `uat` construye en local sin publicar la imagen.
5. Respalda la base mediante la action `backup-db`, salvo que se haya desmarcado `hacer_backup`. Se autentica contra Google por Workload Identity Federation, sin claves de servicio en el repositorio.
6. **Aplica las migraciones siempre en un deploy.** La aplicación ya no ejecuta `db.create_all()` al arrancar: el esquema lo construyen solo las migraciones, así que el `flask db upgrade` dejó de ser opcional.
7. `flask seed-inicial` — siembra roles y usuario administrador.
8. Comprueba que la aplicación responde, reintentando durante un minuto. Si no lo hace, vuelca los últimos logs del contenedor y falla: un despliegue que deja la app caída no debe terminar en verde.

Sobre el paso 6 conviene conocer un detalle, porque ya dio problemas: si el `upgrade` falla **porque la base apunta a una revisión que ya no existe** (lo que ocurre al aplastar migraciones en un baseline), el workflow lo detecta y ejecuta `flask db stamp --purge head`. El `--purge` es imprescindible: `flask db stamp head` a secas resuelve primero la revisión actual contra el historial y muere con el mismo `Can't locate revision` que el upgrade. Cualquier **otro** fallo del upgrade aborta el despliegue en lugar de estampar a ciegas, que dejaría la base marcada como migrada sin haber aplicado una sola sentencia. Al final ejecuta `flask db check`, que **falla** si el esquema real no coincide con los modelos — el stamp declara, no aplica DDL, así que sin esta comprobación una base mal sellada pasaría por buena.

### 3. `db_migrations.yml` — Operaciones de Base de Datos

Manual. Ejecuta comandos de Flask-Migrate **dentro del contenedor `inventario_app` ya desplegado**, para no tener que entrar por SSH al VPS. La entrada `action` acepta:

- **`current`** — muestra en qué revisión está la base.
- **`upgrade`** — aplica las migraciones pendientes.
- **`rollback`** — `downgrade` hasta `rollback_target` (por defecto `-1`, una atrás).
- **`stamp`** — marca la base como si estuviera en `stamp_target` **sin ejecutar SQL de esquema**. Es lo que necesita una base preexistente después de un squash: ya tiene las tablas y no debe recrearlas. Usa `--purge` por el mismo motivo explicado arriba.

Las tres que modifican algo (`upgrade`, `rollback`, `stamp`) hacen respaldo automático antes; `current` no, porque solo lee.

**No existe una acción `migrate`, y es deliberado.** La hubo: autogeneraba la migración contra la base viva y hacía commit y push a la rama desde el runner. Eso saltaba el PR, la revisión y el propio `check_migrations.yml`, además de grabar en el archivo cualquier desviación que tuviera la base de producción. Las migraciones se generan en local, se revisan en un PR y las valida el CI.

### 4. `restore.yml` — Restauración de Datos

Manual, y en tres fases: detiene los contenedores, restaura y los vuelve a levantar. El trabajo real lo delega en un workflow reutilizable de la organización, `SummanTech/infra-templates/.github/workflows/restore-data.yml@main`.

Permite restaurar **de un entorno a otro** (`source_namespace` y `target_namespace` son independientes), así que sirve para bajar datos de producción a `dev`. Se elige qué restaurar —base de datos, volumen de archivos subidos, o ambos— y si la base se recupera contra Azure PostgreSQL o contra un contenedor local, indicando la fecha del respaldo en GCS.

Ambos workflows comparten el grupo de concurrencia `summanpos-<rama>`, así que un despliegue y una operación de base de datos no pueden ejecutarse a la vez sobre el mismo entorno.

### Nota de seguridad

Las acciones destructivas —`destroy` en `deploy.yml` y todo `restore.yml`— traen un control de permisos por usuario, pero **la lista está vacía**:

```bash
AUTHORIZED_USERS=""
```

Tal y como avisa el propio comentario del workflow, con la lista vacía **cualquiera con permiso de ejecución sobre Actions puede destruir un entorno o sobrescribir sus datos**. Conviene rellenarla con los usuarios de GitHub autorizados, o proteger esos entornos con *required reviewers* en la configuración de Environments.

## Despliegue

El despliegue **no es automático al hacer push**: los cuatro workflows salvo `check_migrations.yml` se lanzan a mano desde la pestaña **Actions**, eligiendo la rama y la acción. Un `deploy` sobre la rama elegida:

1. Sincroniza el código en el directorio correspondiente del servidor.
2. Construye las imágenes Docker optimizadas.
3. Levanta los servicios con `docker-compose up` conectándolos a la red compartida correspondiente.
4. Aplica las migraciones de base de datos y siembra los datos iniciales.
5. (En producción) Publica la imagen en el registry central.

## Desarrollo Local

Para levantar el proyecto en un entorno local de desarrollo:

1. Asegúrate de tener Docker y Docker Compose instalados.
2. Configura tu archivo `.env` basándote en los requerimientos del proyecto.
3. Ejecuta `docker-compose up --build` para construir y levantar los contenedores.

## Instrucciones para Inteligencia Artificial y Reglas de Desarrollo

**CRÍTICO - REGLA DE MIGRACIONES DE BASE DE DATOS:**

Toda IA asistente o desarrollador que modifique un archivo de modelo (por ejemplo, los archivos en la carpeta de modelos donde se define la estructura de las tablas de SQLAlchemy) **DEBE OBLIGATORIAMENTE** generar el archivo de migración correspondiente antes de hacer un commit o push.

Si haces un cambio estructural en la base de datos, siempre debes ejecutar:

1. `flask db migrate -m "Descripción del cambio"`
2. Asegurarte de que el nuevo archivo generado en `migrations/versions/` sea agregado al commit.

Existe un GitHub Action (`check_migrations.yml`) que validará esto de forma automatizada y bloqueará cualquier PR o Push que haya modificado un modelo y omitido subir su archivo de migración.

### Las migraciones deben ser compatibles hacia atrás

En un deploy, `docker-compose up -d` levanta el código nuevo **antes** de que corra `flask db upgrade`. Durante esos segundos **el código nuevo se ejecuta contra el esquema viejo**. Si la migración y el código no son compatibles en ambos sentidos, ahí hay errores 500 en producción.

La regla, entonces: **una migración nunca debe romper el código que ya está corriendo, y el código nuevo nunca debe dar por hecho que la migración ya pasó.** En la práctica:

- **Columnas nuevas: siempre `nullable=True` o con `server_default`.** Un `NOT NULL` sin valor por defecto revienta en cuanto el código viejo intente insertar una fila.
- **No renombrar una columna de golpe.** Se añade la nueva, el código escribe en las dos, se copian los datos, y la vieja se elimina en un despliegue **posterior**.
- **No borrar nada en la misma entrega que deja de usarlo.** Primero se despliega el código que ya no la usa; la columna o tabla se elimina en la siguiente. Si hay que revertir el despliegue, los datos siguen ahí.
- **No cambiar el tipo de una columna en sitio.** Mismo patrón: columna nueva, copia, retirada más tarde.
- **Índices sobre tablas grandes:** `op.create_index(..., postgresql_concurrently=True)` para no bloquear escrituras. Requiere que la migración no corra dentro de una transacción.

Es el patrón *expand / contract*: primero se **amplía** el esquema de forma que ambos códigos funcionen, después se migran los datos, y solo en una entrega posterior se **contrae** eliminando lo viejo. Cuesta un despliegue más y evita la ventana de caída.

Lo mismo aplica al `rollback` de `db_migrations.yml`: un `downgrade` solo es seguro si la migración se escribió pensando en que podía revertirse.
