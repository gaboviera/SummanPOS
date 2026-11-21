# Sistema de Roles y Permisos

El sistema de inventario y punto de venta (POS) cuenta con tres niveles de acceso principales para mantener la seguridad y la integridad de los datos. Estos roles son: **Administrador**, **Supervisor** y **Cajero**.

A continuación se detalla qué acciones y módulos están permitidos para cada rol, basándose en la configuración actual de rutas y decoradores de seguridad.

---

## 1. Administrador 👑
Es el rol con mayor nivel de privilegio en el sistema. Tiene acceso total a todos los módulos, reportes y configuraciones.

**Capacidades Exclusivas:**
* **Gestión de Usuarios:** Es el único que puede crear, editar, desactivar o eliminar otros usuarios del sistema, así como asignarles roles.
* **Configuración del Sistema:** Acceso al módulo de configuración general (tasas de cambio, datos de la empresa, identidad visual, etc.).
* **Eliminación de Registros (Soft Delete):** Solo el administrador tiene permiso para eliminar productos, categorías, atributos o contactos.
* **Ajuste Rápido de Stock:** Capacidad de editar el inventario de manera directa desde el Dashboard.
* **Auditoría y Papelera:** Puede ver registros eliminados (como productos en la papelera).
* **Métricas Financieras Completas:** Visualiza todos los indicadores financieros, costos y márgenes de ganancia en el panel principal (Dashboard).

---

## 2. Supervisor 📋
El rol de Supervisor está diseñado para el personal encargado de la gestión operativa del inventario y las compras, pero sin acceso a configuraciones críticas del sistema o gestión de personal.

**Capacidades:**
* **Gestión de Inventario (Limitada):** Puede crear y editar productos, pero **no** puede eliminarlos ni hacer ajustes rápidos de stock en el Dashboard.
* **Compras a Proveedores:** Tiene acceso para crear órdenes de compra y gestionar el ingreso de mercancía al almacén.
* **Categorías y Atributos:** Puede crear y editar la estructura del catálogo (categorías y atributos), pero **no** eliminarlos.
* **Métricas Operativas:** Tiene acceso a la mayoría de las gráficas operativas en el Dashboard, enfocadas en ventas y movimientos de inventario.
* **Ventas y Clientes:** Al igual que el cajero, puede procesar ventas y registrar nuevos contactos/clientes.

**Restricciones:** No puede acceder al módulo de Usuarios, no puede cambiar la Configuración global y no puede realizar borrados en el sistema.

---

## 3. Cajero 🛒
Es el rol base del sistema, diseñado específicamente para la atención al cliente y facturación. Su interfaz es más limpia y restringida para evitar errores humanos en el inventario general.

**Capacidades:**
* **Punto de Venta (Ventas):** Acceso total para generar nuevas ventas, guías de despacho y recibos.
* **Catálogo de Productos:** Puede visualizar el inventario disponible y buscar productos por atributos para informar a los clientes.
* **Gestión de Clientes:** Puede registrar nuevos clientes (Contactos) en el sistema al momento de facturar.
* **Dashboard (Limitado):** Visualiza un panel principal simplificado, orientado solo a sus propias métricas del día o accesos rápidos.

**Restricciones:** No puede crear ni editar productos, categorías, atributos, órdenes de compra, usuarios ni configuraciones. Su menú lateral es reducido para mostrar únicamente las herramientas necesarias para la venta.
