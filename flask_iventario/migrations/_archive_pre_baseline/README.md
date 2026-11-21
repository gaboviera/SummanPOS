# Migraciones anteriores al baseline

Estas 25 migraciones se archivaron al introducir `0001_baseline_esquema_completo`.

## Por que

El historial no era capaz de reconstruir el esquema desde una base de datos
vacia. Once tablas declaradas en `models.py` no las creaba ninguna migracion
(`ordenes_compra`, `detalle_orden_compra`, `ordenes_dropshipping`, `pagos_cxc`,
`pagos_cxp`, `pagos_dropshipping`, `configuracion`, `detalle_dropshipping`,
`listas_precios`, `notificaciones`, `producto_precios`), pero si habia
migraciones que hacian ALTER sobre ellas.

El motivo: en la practica el esquema lo creaba `db.create_all()` al importar
`app.py`, no Alembic. Las migraciones solo registraban los cambios posteriores,
sobre tablas que Alembic nunca habia visto nacer.

Se conservan como referencia historica. Alembic NO las lee: estan fuera de
`versions/`.

## Bases de datos preexistentes

Una base que ya tiene el esquema no debe ejecutar el baseline. Marcarla:

    flask db stamp 0001_baseline

Eso reescribe `alembic_version` al nuevo head sin tocar las tablas.
