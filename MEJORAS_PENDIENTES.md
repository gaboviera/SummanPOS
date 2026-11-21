# Lista de Mejoras Pendientes

Este documento contiene un registro de las mejoras, correcciones y nuevas funcionalidades que deben ser implementadas en el sistema en futuras actualizaciones.

## 1. Módulo de Compras (`/compras/`)
* **Anulación de Órdenes de Compra:** Es necesario implementar la funcionalidad para **anular compras** que ya han sido procesadas o recibidas.
* **Reversión de Stock:** Al anular una orden de compra, el sistema debe revertir o restaurar automáticamente el stock de los productos involucrados en dicha orden.

## 2. Módulo de Tasas de Cambio (`/bcv/historial`)
* **Duplicidad en Ejecución del Cron:** Se ha detectado que el cron job que actualiza las tasas de cambio (BCV y Binance USDT) se está ejecutando múltiples veces en el mismo minuto (por ejemplo, registros duplicados/triplicados a las 08:00 y 08:58). 
* **Acción Requerida:** Revisar la lógica del cron job o el planificador de tareas en el servidor para asegurar que se ejecute una sola vez por intervalo. Adicionalmente, revisar si esta duplicidad está afectando la vista de historial de tasas y la vista de productos.
* **Posible solución en BD:** Modificar el modelo `TasaCambio` para impedir registros duplicados de la misma fuente en el mismo día/hora.

## 3. Pipeline de CI/CD y Migraciones

**Cuándo:** después de que el estado actual de `dev` llegue a producción y se valide allí. Ninguno de estos puntos es urgente; el 3.1 es el único que cambia el comportamiento del despliegue y debe probarse primero en `dev`.

### 3.1 Migrar ANTES de levantar el código nuevo

* **Problema:** hoy `deploy.yml` ejecuta `docker-compose up -d` y *después* `flask db upgrade`. Durante esos segundos el código nuevo corre contra el esquema viejo, que es la combinación que revienta: el código referencia una columna que todavía no existe.
* **Cambio:** invertir el orden en el paso «Ejecutar Acción», separando el `up --build` actual en tres:

  ```bash
  docker-compose build
  docker-compose run --rm inventario_app flask db upgrade   # contenedor efímero de la imagen nueva
  docker-compose up -d --remove-orphans
  ```

* **Detalle técnico:** tiene que ser `run --rm` y no `exec`. `exec` necesita un contenedor ya levantado, y aquí precisamente todavía no lo hay; `run --rm` arranca uno efímero desde la imagen recién construida, aplica las migraciones y se va.
* **Por qué mejora:** la única combinación transitoria pasa a ser *código viejo + esquema nuevo*, que es justo la que el patrón expand/contract del README garantiza que funciona. La disciplina deja de depender de que cada quien se acuerde y pasa a estar respaldada por el orden de los pasos.
* **Ojo:** esto **no sustituye** la regla de migraciones compatibles hacia atrás del README. La sigue necesitando; solo hace que proteja contra el caso fácil en vez del difícil.
* **Al hacerlo:** revisar que el paso de backup siga ocurriendo antes del `upgrade`, y que el bloque de recuperación con `stamp --purge` se mueva junto con él.

### 3.2 Ver el SQL antes de aplicarlo en producción

* `flask db upgrade --sql` imprime las sentencias sin ejecutarlas.
* Añadirlo como paso previo (solo en `main`/`prd`) deja en el log exactamente qué DDL se va a correr. En `dev` sería ruido.
* Sirve para enterarse **antes** de que una migración iba a reescribir una tabla grande.

### 3.3 Avisar de las migraciones destructivas en el CI

* `check_migrations.yml` verifica hoy que la migración *exista*, no qué hace.
* Añadir un paso que busque `drop_column`, `drop_table` o `alter_column(..., nullable=False)` en los archivos nuevos del PR y lo marque con un aviso (`::warning::`).
* No hace falta bloquear el PR: basta con que no pasen desapercibidos dentro de un diff grande.

### 3.4 Verificar que el `downgrade` funciona

* El CI ya aplica la cadena completa sobre una base limpia. Añadirle `flask db downgrade base` y volver a subir cuesta segundos.
* Hoy la acción `rollback` de `db_migrations.yml` existe pero **nadie ha comprobado nunca que las migraciones sean reversibles**. El día que haga falta de urgencia no es el momento de descubrirlo.

### 3.5 Comprobar que hay una sola cabeza de migración

* Un `flask db heads` que falle si devuelve más de una línea.
* Es una línea de bash y detecta al instante el error que ya costó un despliegue: dos ramas de migración conviviendo tras un merge.

### 3.6 Control de acceso real para las acciones destructivas

* `AUTHORIZED_USERS=""` está vacío en `deploy.yml` (acción `destroy`) y en `restore.yml`, así que la condición siempre pasa.
* El problema de fondo no es la lista vacía sino **dónde vive**: dentro del propio workflow, donde cualquiera que pueda empujar a una rama la edita y se añade.
* La solución no es código: son *required reviewers* en los Environments de GitHub (Settings → Environments), que no se pueden saltar desde una rama.

