# Manual de Usuario Integral — SummanPOS (InvenTrack Pro)

> **Sistema de Planificación de Recursos Empresariales (Mini-ERP) y Punto de Venta (POS) Especializado en Repuestos y Comercio General Multimoneda**
> 
> **Entorno de Producción/Staging:** [https://dev-mini-erp.summantech.com/](https://dev-mini-erp.summantech.com/)  
> **Versión del Manual:** Edición Definitiva 2026 (Exhaustiva con Formularios y Modales)  
> **Arquitectura:** Python 3 (Flask) + PostgreSQL + SQLAlchemy + WTForms + Bootstrap 5  
> **Régimen Fiscal:** Multimoneda (USD, Bs BCV, EUR BCV, USDT Binance) con IVA (16%) e IGTF (3%)  

---

## Ficha de Metadatos del Sistema

| Parámetro | Especificación |
| :--- | :--- |
| **Nombre Comercial** | SummanPOS / InvenTrack Pro |
| **URL del Sistema** | `https://dev-mini-erp.summantech.com/` |
| **Acceso Administrativo Inicial** | Usuario: `admin` / Contraseña: `admin123` |
| **Desarrollo y Arquitectura** | SummanTech Engineering Swarm |
| **Formatos Entregables** | Documento Word (`.docx`, 10.2 MB), Documento PDF (`.pdf`, 61 páginas, 10.2 MB), Manual Web (`.html`, 14.8 MB), Fuente Markdown (`.md`) |
| **Público Objetivo** | Cajeros, Vendedores en Mostrador, Jefes de Almacén, Analistas de Finanzas y Gerentes Generales |

---

## Tabla de Contenidos

1. [Capítulo 1: Introducción, Arquitectura y Paleta Corporativa](#capítulo-1-introducción-arquitectura-y-paleta-corporativa)
2. [Capítulo 2: Control de Acceso, Autenticación y Gestión de Usuarios](#capítulo-2-control-de-acceso-autenticación-y-gestión-de-usuarios)
3. [Capítulo 3: Panel de Control (Dashboard), Métricas KPIs y Cotizaciones](#capítulo-3-panel-de-control-dashboard-métricas-kpis-y-cotizaciones)
4. [Capítulo 4: Módulo de Inventario y Catálogo Maestro de Productos](#capítulo-4-módulo-de-inventario-y-catálogo-maestro-de-productos)
5. [Capítulo 5: Módulo de Punto de Venta (POS) y Facturación Multimoneda](#capítulo-5-módulo-de-punto-de-venta-pos-y-facturación-multimoneda)
6. [Capítulo 6: Módulo de Compras y Abastecimiento a Proveedores](#capítulo-6-módulo-de-compras-y-abastecimiento-a-proveedores)
7. [Capítulo 7: Módulo Especializado de Dropshipping](#capítulo-7-módulo-especializado-de-dropshipping)
8. [Capítulo 8: Módulo de Finanzas y Tesorería (CxC, CxP y Flujo de Pagos)](#capítulo-8-módulo-de-finanzas-y-tesorería-cxc-cxp-y-flujo-de-pagos)
9. [Capítulo 9: Configuración del Sistema, Identidad de Marca y Parámetros](#capítulo-9-configuración-del-sistema-identidad-de-marca-y-parámetros)
10. [Capítulo 10: Centro de Notificaciones y Alertas en Tiempo Real](#capítulo-10-centro-de-notificaciones-y-alertas-en-tiempo-real)
11. [Capítulo 11: Glosario de Términos, FAQ y Resolución de Incidencias Operativas](#capítulo-11-glosario-de-términos-faq-y-resolución-de-incidencias-operativas)

---

## Capítulo 1: Introducción, Arquitectura y Paleta Corporativa

**SummanPOS** es una plataforma integral diseñada para simplificar la administración de inventarios extensos, acelerar las ventas en mostrador y gestionar con exactitud contable operaciones comerciales en economías multimoneda.

El sistema opera de forma transparente y concurrente con cuatro cotizaciones:
- **Dólar Estadounidense ($):** Moneda contable principal y base de costo.
- **Bolívares (Bs) BCV:** Tasa oficial diaria del Banco Central de Venezuela.
- **Euros (€) BCV:** Tasa oficial para operaciones vinculadas a Europa.
- **USDT Binance P2P:** Promedio en tiempo real del mercado criptoactivo.

![Landing Page](./screenshots/01_landing_page.png)
*Figura 1.1: Portal público de acceso al sistema SummanPOS.*

---

## Capítulo 2: Control de Acceso, Autenticación y Gestión de Usuarios

El acceso está restringido mediante credenciales con contraseñas cifradas con el estándar **Bcrypt**. La autorización se controla mediante el decorador `@rol_requerido`.

![Login](./screenshots/02_login_seguridad.png)
*Figura 2.1: Interfaz de Inicio de Sesión Seguro (Login).*

### 2.1 Panel de Gestión de Usuarios (`/usuarios`)

Desde `/usuarios` el Administrador audita todas las cuentas registradas, su rol de acceso y estado activo/inactivo.

![Panel Usuarios](./screenshots/25_configuracion_usuarios.png)
*Figura 2.2: Tabla Maestra de Gestión de Usuarios y Roles.*

### 2.2 Procedimiento Paso a Paso para Crear Nuevo Usuario

Al presionar **'Nuevo Usuario'**, se abre el modal `#usuarioModal`:

![Modal Nuevo Usuario](./screenshots/26_usuario_modal_nuevo.png)
*Figura 2.3: Modal Interactivo para Alta de Nuevo Usuario.*

| Campo del Modal | Tipo | Obligatorio | Regla de Negocio y Validación |
| :--- | :--- | :---: | :--- |
| **Usuario o Correo** | Texto / Email | **SÍ** | Longitud entre 3 y 50 caracteres. Formato alfanumérico o correo válido sin espacios ni caracteres extraños. |
| **Contraseña** | Password | **SÍ** | Mínimo 6 caracteres. Dispone de botón interactivo para mostrar u ocultar la clave mientras se tipea. |
| **Rol de Acceso** | Select | **SÍ** | Asigna privilegios: **Administrador**, **Supervisor** o **Cajero / Vendedor**. |
| **Usuario Activo** | Switch Toggle | **SÍ** | Permite activar o suspender el acceso de un operador sin borrar su historial contable. |

![Modal Llenado](./screenshots/27_usuario_modal_llenado.png)
*Figura 2.4: Formulario de Usuario Completado con Selección de Rol y Clave Oculta.*

### 2.3 Procedimiento para Editar Usuarios Existentes

Al hacer clic en el botón amarillo con icono de lápiz, el modal se abre en modo 'Editar Usuario' con los datos precargados:

![Modal Editar Usuario](./screenshots/28_usuario_modal_editar.png)
*Figura 2.5: Modal de Edición de Usuario (permite cambiar roles sin afectar la clave existente).*

> [!CAUTION]
> **Salvaguarda de Seguridad:** El sistema impide eliminar al último usuario con rol Administrador para garantizar que nunca se pierda el acceso al sistema.

---

## Capítulo 3: Panel de Control (Dashboard), Métricas KPIs y Cotizaciones

El Dashboard (`/dashboard`) proporciona visibilidad en tiempo real de la jornada comercial, inventario crítico y tasas oficiales.

![Dashboard](./screenshots/03_dashboard_gerencial.png)
*Figura 3.1: Tablero Central con KPIs, Tasas BCV en Vivo y Tendencia Semanal.*

- **Ventas Hoy ($ USD y Bs):** Ingresos brutos recaudados en la jornada con cálculo multimoneda inmediato.
- **Órdenes Hoy:** Total de facturas y notas de despacho emitidas en el día.
- **Semáforo de Bajo Stock:** Alerta de referencias con existencia crítica (≤ 5 unidades).
- **Tendencia de Ventas (7 Días):** Comparativa diaria de facturación.
- **Cotizaciones Oficiales y Cripto:** Tasas Dólar BCV, Euro BCV y Binance USDT P2P automatizadas mediante APScheduler.

---

## Capítulo 4: Módulo de Inventario y Catálogo Maestro de Productos

### 4.1 Catálogo Maestro de Repuestos (`/productos`)

![Catálogo](./screenshots/04_inventario_catalogo.png)
*Figura 4.1: Catálogo Maestro de Inventario con Filtros y Semáforo de Existencias.*

### 4.2 Formulario de Alta de Repuestos (`/productos/nuevo`)

![Nuevo Producto](./screenshots/05_inventario_nuevo_producto.png)
*Figura 4.2: Formulario de Creación de Producto con Atributos Dinámicos.*

### 4.3 Formulario de Edición de Repuestos (`/productos/editar/<id>`)

![Editar Producto](./screenshots/43_inventario_editar_producto.png)
*Figura 4.3: Formulario de Edición de Producto con Precios Excepcionales por Lista.*

### 4.3 Lista de Precios al Consumidor y Matriz Multimoneda (`/productos/lista-precios`)

La pantalla de **Lista de Precios al Consumidor** (`/productos/lista-precios`) es la herramienta central para consulta rápida de tarifas en mostrador, atención telefónica y cotización a clientes. Ofrece visibilidad inmediata de precios calculados en tiempo real bajo las distintas divisas y esquemas comerciales de la empresa sin exponer márgenes ni datos confidenciales del catálogo:

| Modalidad de Precio | Moneda Base / Cotización | Fórmula y Regla de Negocio | Uso Operativo |
| :--- | :--- | :--- | :--- |
| **💵 Efectivo ($ USD)** | Dólar Estadounidense ($) | `Precio Base` fijado en catálogo. | Venta de mostrador en divisas en efectivo. |
| **🏛️ Precio BCV ($ y Bs)** | Bolívares (Bs) BCV | `(Precio Base × Regla BCV) × Tasa BCV` (ej. +20%). | Pagos en Bolívares (Pago Móvil, Punto de Venta). |
| **⚡ Precio USDT ($ y Bs)** | Binance P2P USDT | `Precio Base × Regla USDT` (paridad o recargo). | Cobros en Binance Pay / criptoactivos. |
| **💶 Precio Euro ($ y Bs)** | Euro BCV Oficial | `Precio Base × Regla Euro` a tasa europea. | Operaciones y presupuestos en Euros. |
| **📦 Mayorista ($ USD)** | Dólar Mayorista | `Precio Base × (1 - Descuento Mayorista)` (ej. -15%). | Tarifa especial para talleres y distribuidores. |

![Lista de Precios](./screenshots/06_inventario_lista_precios.png)
*Figura 4.4: Pantalla Principal de Lista de Precios al Consumidor con Widgets de Tasas y Matriz Multimoneda.*

> [!NOTE]
> **Widgets en Vivo y Banner de Reglas:** En la barra superior se visualizan en tiempo real las cotizaciones del BCV y Binance USDT, con botón de actualización inmediata en un clic (`/bcv/actualizar`). Debajo, un banner dinámico detalla los porcentajes exactos aplicados sobre el costo base.

#### 4.3.1 Personalización de Columnas y Filtros de Visualización

- **Selector de Resaltado por Moneda:** Permite enfocar la vista en una moneda específica (`💵 Efectivo`, `🏛️ BCV`, `⚡ USDT`, `💶 Euro` o `📦 Mayorista`). Al pulsar cualquiera de estos botones, el sistema atenúa automáticamente las demás columnas al 30% de opacidad para evitar distracciones en mostrador.
- **Dropdown Mostrar/Ocultar Columnas con Persistencia:** Permite activar o desactivar columnas (Código, Repuesto, Categoría, Marca, Stock y Precios individuales). Las preferencias se guardan de forma persistente en `localStorage`.
- **Filtro Multicriterio y Dropshipping:** Búsqueda en vivo por código o descripción, selector de categorías, filtro por existencia (`Solo con Stock` / `Agotados`) y origen (`Solo Físico` / `Solo Dropshipping`).
- **Barra Flotante de Selección Masiva:** Al marcar los checkboxes de los productos deseados, se despliega una barra superior con contador en vivo para ejecutar exportaciones selectivas.

![Selector de Columnas](./screenshots/47_lista_precios_selector_columnas.png)
*Figura 4.5: Menú Interactivo de Personalización de Columnas Visibles y Filtros Rápidos de Moneda.*

#### 4.3.2 Asistente de Exportación e Impresión Profesional (`#modalExportarPrecios`)

Al pulsar el botón azul **'Exportar / Imprimir'**, se despliega el asistente modal estructurado en 3 pasos clave:

1. **Formato de Descarga:** Hoja de cálculo Excel (`.xlsx`) con fórmulas editables o Documento PDF (`.pdf`) formal con membrete corporativo, fecha de emisión y tabla maquetada.
2. **Precios y Moneda:** Exportar solo BCV ($ y Bs), solo Efectivo ($), solo USDT ($ y Bs), solo Mayorista ($) o Matriz Comparativa Completa de todas las listas en columnas.
3. **Alcance de Productos y Stock:** Solo Seleccionados, Catálogo Completo o Solo Filtrados, con switch para incluir u omitir la columna de existencias físicas.

![Modal Exportar Precios](./screenshots/46_lista_precios_modal_exportar.png)
*Figura 4.6: Asistente Modal de Exportación e Impresión con Selección de Formato (Excel / PDF), Regla Tarifaria y Alcance.*

### 4.4 Kardex Oficial de Movimientos de Inventario (`/transacciones`)

![Kardex](./screenshots/07_inventario_kardex_movimientos.png)
*Figura 4.7: Kardex Oficial de Transacciones con Trazabilidad Inmutable.*

### 4.5 Carga Masiva vía Excel (`/importar`)

![Carga Masiva](./screenshots/08_inventario_carga_masiva.png)
*Figura 4.8: Módulo de Importación Masiva en Segundo Plano vía Excel (.xlsx).*

---

## Capítulo 5: Módulo de Punto de Venta (POS) y Facturación Multimoneda

Optimizado para despacho rápido en mostrador con escaneo de código de barras o búsqueda en vivo.

![Punto de Venta](./screenshots/09_pos_punto_de_venta.png)
*Figura 5.1: Terminal POS con Carrito Interactivo, Cálculo de Margen y Desglose Fiscal.*

### Régimen Impositivo Venezolano (IVA 16% e IGTF 3%)
1. $\text{Total Bruto} = \sum (\text{Cantidad} \times \text{Precio de Lista con Descuento de Ítem})$
2. $\text{Base Imponible} = \text{Total Bruto} - \text{Descuento Global}$
3. $\text{IGTF (3\%)} = \text{Base Imponible} \times 0.03$
4. $\text{Sub-Total} = \text{Base Imponible} + \text{IGTF}$
5. $\text{IVA (16\%)} = \text{Base Imponible} \times 0.16$ (gravado únicamente sobre la Base Imponible)
6. $\text{Total Final a Pagar (USD)} = \text{Base Imponible} \times 1.19$
7. $\text{Total en Bolívares (Bs)} = \text{round}(\text{round}(\text{Total USD}, 2) \times \text{Tasa BCV}, 2)$

### Pasarela de Pagos Multimoneda y Detección de Fuga de Margen

![Modal Cobro](./screenshots/09_pos_modal_cobro.png)
*Figura 5.2: Modal de Cobro con Soporte Multimoneda y Calculadora Rápida.*

> [!WARNING]
> **Fuga de Margen:** Si la cotización está en Precio Base (USD) pero el cliente paga en Bolívares (Pago Móvil / Punto de Venta), el sistema lanza una alerta roja para advertir la pérdida cambiaria y permite ajustar a Precio BCV con un clic.

### Historial y Comprobante Oficial de Entrega

![Historial Ventas](./screenshots/10_pos_historial_ventas.png)
*Figura 5.3: Historial de Ventas con Estados de Pago y Reimpresión de Comprobantes.*

![Recibo Venta](./screenshots/40_ventas_recibo_impresion.png)
*Figura 5.4: Comprobante Oficial de Entrega con Desglose Fiscal y Firmas.*

---

## Capítulo 6: Módulo de Compras y Abastecimiento a Proveedores

![Órdenes de Compra](./screenshots/11_compras_ordenes.png)
*Figura 6.1: Tablero Central de Órdenes de Compra a Proveedores.*

![Nueva Compra](./screenshots/12_compras_nueva_orden.png)
*Figura 6.2: Registro de Orden de Compra a Proveedor con Precios Pactados.*

### Recepción en Almacén y Comprobante de Compra

![Recepción Mercancía](./screenshots/37_compras_recibir_mercancia.png)
*Figura 6.3: Formulario de Recepción de Mercancía en Almacén con Validación Estricta.*

![Recibo Compra](./screenshots/38_compras_recibo_detalle.png)
*Figura 6.4: Comprobante Formal de Orden de Compra a Proveedor.*

---

## Capítulo 7: Módulo Especializado de Dropshipping

Venta de mercancía por encargo directo donde el proveedor aliado despacha al comprador final.

![Dropshipping](./screenshots/13_dropshipping_ordenes.png)
*Figura 7.1: Panel de Control de Órdenes de Dropshipping y Envíos por Courier.*

![Nuevo Dropshipping](./screenshots/14_dropshipping_nueva_orden.png)
*Figura 7.2: Formulario de Creación de Orden Dropshipping.*

![Tracking Dropshipping](./screenshots/39_dropshipping_detalle_tracking.png)
*Figura 7.3: Detalle de Orden Dropshipping con Asignación de Courier y Comisión Neta.*

![Catálogo Dropshipping](./screenshots/15_dropshipping_productos.png)
*Figura 7.4: Historial y Desempeño de Artículos en Dropshipping.*

---

## Capítulo 8: Módulo de Finanzas y Tesorería (CxC, CxP y Flujo de Pagos)

![Cuentas por Cobrar](./screenshots/16_finanzas_cxc.png)
*Figura 8.1: Cuentas por Cobrar (CxC) con Control de Vencimiento y Cobro Asistido por WhatsApp.*

### Modales de Registro de Abonos y Calculadora en Bolívares

![Modal Abono CxC](./screenshots/33_cxc_modal_abono.png)
*Figura 8.2: Modal para Registrar Abono a Cliente con Saldo Pendiente.*

![Calculadora Abono](./screenshots/34_cxc_modal_calculadora.png)
*Figura 8.3: Calculadora Rápida en Bolívares con Tasa BCV, USDT y Euro.*

![Historial Abonos](./screenshots/35_cxc_modal_historial.png)
*Figura 8.4: Historial Cronológico de Abonos de una Nota de Entrega.*

### Cuentas por Pagar (CxP) Consolidada y Modal de Pago

![Cuentas por Pagar](./screenshots/17_finanzas_cxp.png)
*Figura 8.5: Cuentas por Pagar Consolidando Compras y Dropshipping.*

![Modal Pago CxP](./screenshots/36_cxp_modal_abono.png)
*Figura 8.6: Modal para Registrar Pago / Abono a Proveedor.*

![Historial Pagos](./screenshots/18_finanzas_historial_pagos.png)
*Figura 8.7: Flujo Centralizado de Cobros (Verde) y Desembolsos (Rojo).*

---

## Capítulo 9: Configuración del Sistema, Identidad de Marca y Parámetros

### 9.1 Directorio y Modales de Contactos (`/contactos`)

![Contactos](./screenshots/19_configuracion_contactos.png)
*Figura 9.1: Directorio Centralizado de Clientes y Proveedores.*

![Modal Nuevo Contacto](./screenshots/29_contacto_modal_nuevo.png)
*Figura 9.2: Modal para Crear Nuevo Contacto (Cliente / Proveedor / Ambos).*

![Modal Contacto Llenado](./screenshots/30_contacto_modal_llenado.png)
*Figura 9.3: Formulario de Contacto con Datos Fiscales y Dirección Completados.*

### 9.2 Categorías y Atributos Dinámicos

![Categorías](./screenshots/20_configuracion_categorias.png)
*Figura 9.4: Catálogo de Familias y Categorías de Inventario.*

![Modal Editar Categoría](./screenshots/31_categoria_modal_editar.png)
*Figura 9.5: Modal de Edición Rápida de Nombre de Categoría.*

![Atributos](./screenshots/21_configuracion_atributos.png)
*Figura 9.6: Administración de Atributos de Repuestos (Estilo Odoo).*

![Valores Atributos](./screenshots/32_atributos_gestion_valores.png)
*Figura 9.7: Gestión de Valores Específicos por Atributo (Marcas, Modelos, Años).*

### 9.3 Historial de Cotizaciones y Formulario de Tasa Manual

![Historial Tasas](./screenshots/22_configuracion_tasas_bcv.png)
*Figura 9.8: Historial de Cotizaciones Oficiales y Cripto.*

![Tasa Manual](./screenshots/42_tasas_bcv_fijacion_manual.png)
*Figura 9.9: Formulario de Contingencia para Fijación Manual de Cotizaciones.*

### 9.4 Identidad de Marca y Listas de Precios

![Marca](./screenshots/23_configuracion_marca.png)
*Figura 9.10: Configuración de Marca, Logotipo y Datos Fiscales.*

![Listas Precios](./screenshots/24_configuracion_listas_precios.png)
*Figura 9.11: Parametrización de Listas de Precios y Reglas de Margen.*

![Modal Nueva Lista](./screenshots/41_lista_precios_modal_nueva.png)
*Figura 9.12: Modal para Creación de Nueva Regla Comercial por Lista de Precios.*

---

## Capítulo 10: Centro de Notificaciones y Alertas en Tiempo Real

![Notificaciones](./screenshots/45_notificaciones_historial.png)
*Figura 10.1: Historial Centralizado de Alertas del Sistema.*

---

## Capítulo 11: Glosario de Términos, FAQ y Resolución de Incidencias Operativas

### Glosario Técnico-Comercial
- **Base Imponible:** Monto neto de la transacción sobre el cual se calculan los impuestos de ley.
- **IGTF (3%):** Impuesto a las Grandes Transacciones Financieras aplicable en Venezuela sobre la base imponible.
- **IVA (16%):** Impuesto al Valor Agregado calculado exclusivamente sobre la base imponible (sin impuesto sobre impuesto).
- **Tasa BCV:** Cotización oficial diaria del Banco Central de Venezuela.
- **Tasa USDT Binance:** Promedio en tiempo real de cotizaciones en el mercado P2P.
- **Fuga de Margen:** Desbalance que ocurre al cotizar en una moneda y cobrar en otra sin compensar la tasa de cambio.
- **Kardex:** Libro de registro inmutable que audita cada variación de existencias físicas en almacén.
- **Soft Delete:** Baja lógica donde el registro se oculta pero permanece auditable y recuperable en base de datos.

### Preguntas Frecuentes (FAQ)
**P: ¿Cómo crear un nuevo usuario cajero en el sistema?**  
R: Diríjase a Configuración -> Usuarios, haga clic en 'Nuevo Usuario', digite el usuario o correo, ingrese una clave de 6 o más caracteres, seleccione el rol 'Cajero', confirme que el switch esté activo y presione 'Guardar Usuario'.

**P: ¿Cómo cambiar la contraseña de un usuario existente?**  
R: En el panel de Usuarios, ubique al usuario y haga clic en el botón amarillo con icono de lápiz. En el modal que se abre, ingrese la nueva clave en el campo 'Contraseña' y guarde los cambios. Si no desea modificar la clave, deje el campo en blanco.

**P: ¿Cómo recibir parcialmente una compra si el proveedor no envió todas las piezas?**  
R: En Compras -> Órdenes de Compra, presione 'Recibir Mercancía'. En la columna 'Recibiendo AHORA', ingrese únicamente las unidades recibidas físicamente. La orden pasará al estado 'Parcial' y preservará el resto para una entrega posterior.

---
*Manual oficial expandido generado y certificado para SummanPOS (InvenTrack Pro).*
