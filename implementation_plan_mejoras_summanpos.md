# Plan de Implementación de Mejoras (SummanPOS)

Este documento detalla las próximas mejoras en el sistema, adaptadas a los últimos comentarios, eliminando lo relacionado con integración fiscal o módulos contables complejos, y enfocándonos en la gestión práctica de los precios en el punto de venta, cuentas por cobrar, y carga masiva de clientes.

## 1. Modificaciones en el Módulo de Ventas (Punto de Venta / Despacho) - SOLICITUD ACTUAL

Se busca poder alterar el precio de un repuesto únicamente para la orden de venta que se está registrando, pudiendo establecer el precio basado en un porcentaje de ganancia o escribiéndolo directamente, y visualizando el costo del producto.

### Cambios Propuestos:

#### Base de Datos (models.py):
Añadir las columnas `precio_unitario` y `costo_unitario` a la tabla `Transacciones`. 
> [!NOTE]
> Actualmente el sistema no guarda el precio histórico por ítem, por lo que si editas el precio para una venta específica, el sistema debe ser capaz de recordarlo a futuro.

#### Backend (ventas_routes.py y ventas_service.py):
- Modificar `/api/productos` para que envíe también el costo del producto al frontend.
- Actualizar el servicio de registro de ventas para que tome el precio personalizado enviado desde el carrito y lo guarde en la base de datos junto a la transacción.

#### Frontend (ventas.html):
Añadir las siguientes columnas a la tabla del carrito: **Costo**, **Margen (%)**, **Precio Venta**.

#### Lógica JS:
- Al ingresar un producto, mostrará su costo base.
- Si el usuario edita el campo Margen (%), el Precio Venta se calculará automáticamente (Ej: Costo 10 + 30% = 13).
- Si el usuario edita directamente el Precio Venta, el Margen (%) se recalculará automáticamente.
- El Subtotal de la fila se calculará en base al nuevo precio de venta personalizado.

---

## 2. Futuras Implementaciones Acordadas

### A. Carga Masiva por Excel (Solo Clientes)
- Crearemos un módulo en el menú de contactos para subir un archivo Excel/CSV que registre clientes masivamente en la base de datos, omitiendo los duplicados por RIF o correo.
- Se habilitará un botón para descargar una plantilla de Excel en blanco con el formato correcto.

### B. Módulo de Cuentas por Cobrar (CxC)
- Un módulo dedicado para dar seguimiento exclusivo a los clientes con créditos pendientes.
- Podrás ver una lista de "Quiénes deben", "Cuánto deben", "Abonos realizados" y "Días de mora / Días sin pagar".

---

## User Review Required

> [!IMPORTANT]
> **¿Cómo prefieres que se calcule matemáticamente el porcentaje de ganancia?**
> - **Opción A (Markup sobre costo):** `Precio = Costo + (Costo * % / 100)` (Ej: Si cuesta 100 y le gano el 30%, lo vendo a 130).
> - **Opción B (Margen sobre venta):** `Precio = Costo / (1 - % / 100)` (Ej: Si cuesta 100 y quiero que el 30% del precio final sea ganancia, lo vendo a 142.85).
> 
> Asumiré la Opción A si no me indicas lo contrario, ya que es la más común.

> [!WARNING]
> Dado que modificaré la base de datos para guardar el precio histórico de cada repuesto vendido (necesario para que tu precio editado se guarde con éxito en el recibo), se generará una nueva migración con GitHub Actions / Flask-Migrate.

**Si estás de acuerdo con todo lo planteado para la pantalla de Ventas, haz clic en "Proceed" (Proceder) y comenzaré a editar el código y lanzar las modificaciones del carrito y base de datos inmediatamente.**
