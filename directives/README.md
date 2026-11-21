# directives/ (Capa 1: Directivas / SOPs)

Este directorio almacena las directivas de operación (Procedimientos Operativos Estándar o SOPs) en Markdown. Cada directiva describe **un flujo repetible** de este repositorio.

## Índice

| Directiva | Objetivo |
| :--- | :--- |
| [`actualizar_manual_usuario_docx.md`](actualizar_manual_usuario_docx.md) — Actualizar el Manual de Usuario (.docx) | regenerar el manual Word/PDF con capturas nuevas tomadas con Playwright y portada institucional opcional, mediante `agents_scripts/actualizar_manual_docx.py`. |
| [`commit_y_push.md`](commit_y_push.md) — Commit y push seguro | llevar cambios a GitHub sin exponer credenciales y sin desalinear la documentación multi-agente. |
| [`crear_y_aplicar_migraciones.md`](crear_y_aplicar_migraciones.md) — Crear y aplicar migraciones de base de datos | generar en local la migración Alembic de cada cambio de modelos, hacerla pasar por PR y CI, y operarla en los entornos desplegados solo mediante `deploy.yml` o `db_migrations.yml`. |
| [`desplegar_summanpos.md`](desplegar_summanpos.md) — Desplegar SummanPOS | desplegar, reiniciar o destruir SummanPOS (`flask_iventario/`) en el entorno de la rama elegida mediante el workflow manual `deploy.yml`, con respaldo previo y migraciones aplicadas. |
| [`diagnosticar_con_agents_scripts.md`](diagnosticar_con_agents_scripts.md) — Diagnosticar SummanPOS con agents_scripts | inspeccionar el estado de SummanPOS (contenedores y logs en el VPS, o el render de recibos en local) con los scripts existentes de `agents_scripts/`, sin exponer credenciales ni modificar la base. |
| [`generar_manual_tecnico.md`](generar_manual_tecnico.md) — Generar el Manual Técnico | producir el manual técnico Word/PDF (stack, arquitectura, DER, diccionario de datos, rutas, despliegue, seguridad) desde el código real de `flask_iventario/`. |
| [`restaurar_datos.md`](restaurar_datos.md) — Restaurar datos de SummanPOS desde GCS | restaurar la base de datos y/o el volumen de archivos subidos de SummanPOS en un entorno, a partir de un respaldo diario en Google Cloud Storage, mediante el workflow manual `restore.yml`. |

> Mantén este índice al día: toda directiva nueva se agrega aquí en el mismo commit que la crea.

## ¿Qué es una Directiva?
Define **qué hacer**:
- Objetivo claro del proceso.
- Entradas requeridas (archivos, argumentos, variables, secretos por nombre — nunca su valor).
- Herramientas y scripts a usar (`agents_scripts/<script>.py`, `scripts/`, workflows de `.github/workflows/`).
- Salidas esperadas y ubicación (archivos intermedios en `.tmp/`, entregables finales).
- Casos extremos, manejo de errores y restricciones conocidas de APIs o sistemas.

## Formato de una directiva

```markdown
# <Nombre del flujo>

**Objetivo:** una o dos líneas.
**Cuándo usarla:** qué pedido o situación la dispara.

## Entradas
## Herramientas
## Pasos
## Salidas
## Casos extremos y errores conocidos
## Historial de aprendizajes
- YYYY-MM-DD — aprendizaje concreto de este flujo.
```

## Cuándo crear, actualizar o reescribir

- **Crear (obligatorio, sin pedir permiso):** al terminar un flujo de varios pasos que probablemente se repita, al agregar un script nuevo en `agents_scripts/` o `scripts/` que ninguna directiva referencia, o al ejecutar una tarea para la que no existe directiva. Regístrala en el índice.
- **Actualizar (obligatorio):** cuando descubras un límite de API, un caso borde, un error recurrente o un paso mejor. Agrega el aprendizaje en la sección *Historial de aprendizajes* de la directiva — no en `CLAUDE.md`.
- **Reescribir o eliminar (requiere confirmación del usuario):** cambiar el objetivo o el flujo principal de una directiva existente, o borrarla.

## Ciclo de Mejora Continua
1. Antes de iniciar una tarea, el agente busca en el índice la directiva correspondiente y la lee.
2. Si no existe, ejecuta la tarea y al terminar crea la directiva.
3. Si se descubre un límite, un caso borde o una optimización, se actualiza la directiva para que las siguientes sesiones se beneficien del aprendizaje.
