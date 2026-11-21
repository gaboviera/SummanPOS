# Guía de Desarrollo por Fases: Sistema de Inventario de Repuestos Automotrices (Flask + PostgreSQL)

¡Hola! Como tu tutor, te guiaré paso a paso en la construcción de este sistema de inventario para la venta al mayor de repuestos. He adaptado la guía que me proporcionaste a nuestro contexto, priorizando la **seguridad** (manejo seguro de contraseñas, protección CSRF, validación de datos) y **buenas prácticas** (arquitectura en capas, variables de entorno, migraciones).

## User Review Required
> [!IMPORTANT]
> Revisa las entidades de la base de datos en la Fase 3. ¿Falta alguna entidad importante para tu negocio (por ejemplo, manejo de múltiples almacenes, créditos a clientes)?

## Open Questions
> [!NOTE]
> 1. ¿Utilizaremos algún framework CSS en particular para el Frontend (TailwindCSS, Bootstrap) o prefieres CSS puro?
> 2. ¿Deseas que implementemos un sistema de roles estricto desde el principio (Ej. Administrador vs Almacenista)?

## Fases de Implementación

---

### FASE 1: Preparación del Entorno y Dependencias
**Objetivo:** Configurar el entorno de trabajo seguro e instalar las librerías base.

**Lo que haremos:**
1. Crear un entorno virtual para aislar dependencias.
2. Instalar el stack: Flask, SQLAlchemy, PostgreSQL adapter (`psycopg2-binary`), utilidades de seguridad (Bcrypt para contraseñas, Flask-WTF para CSRF).
3. Configurar `.env` cuidando no exponer credenciales.

---

### FASE 2: Configuración de Base de Datos y Extensiones
**Objetivo:** Configurar las extensiones principales (`db` y `migrate`) en un archivo separado para evitar dependencias circulares, una excelente práctica de arquitectura en Flask.

**Lo que haremos:**
1. Crear `extensions.py`.
2. Crear la fábrica de aplicaciones (`create_app`) en `app.py` o `__init__.py` para inicializar extensiones de forma segura.

---

### FASE 3: Definición de Modelos (Capa de Datos)
**Objetivo:** Traducir las entidades del negocio de venta de repuestos al mayor a tablas de base de datos.

**Entidades clave propuestas:**
- `Usuario` (Empleados del sistema con roles)
- `Cliente` (Mayoristas a los que se les vende)
- `Proveedor` (De donde vienen los repuestos)
- `Categoria` (Ej. Frenos, Eléctrico, Motor)
- `Repuesto` (El producto en sí, con SKU, precio mayorista, compatibilidad de vehículos)
- `MovimientoInventario` (Entradas y salidas, para trazabilidad estricta)
- `Pedido/Venta` (Las órdenes al mayor) y su `DetallePedido`.

**Lo que haremos:**
1. Crear `models.py`.
2. Inicializar Alembic y crear la primera migración de tablas.

---

### FASE 4: Capa de Formularios (WTForms)
**Objetivo:** Crear validaciones estrictas tanto en Frontend como en Backend para evitar inyecciones y datos corruptos.

**Lo que haremos:**
1. Crear `forms.py`.
2. Incluir validadores de longitud, tipos de datos, y tokens CSRF habilitados por defecto en todas las peticiones POST.

---

### FASE 5: Capa de Servicios (Lógica de Negocio)
**Objetivo:** Separar las reglas del negocio de las rutas (controladores) para un código más mantenible y testeable.

**Lo que haremos:**
1. Crear `services/inventario_service.py` (manejo de stock, alertas de poco inventario).
2. Crear `services/ventas_service.py` (lógica de facturación, validación de stock antes de vender).
3. Crear `services/auth_service.py` (login y hasheo con Bcrypt).

---

### FASE 6: Rutas y Controladores
**Objetivo:** Definir los Endpoints web.

**Lo que haremos:**
1. Implementar Blueprint en Flask (para organizar mejor las rutas: `/auth`, `/inventario`, `/ventas`).
2. Proteger rutas con decoradores (`@login_required` o validación de roles).

---

### FASE 7: Plantillas e Interfaz (Frontend)
**Objetivo:** Interfaz gráfica amigable y responsiva.

**Lo que haremos:**
1. Diseño de Dashboard.
2. Vistas de catálogo y gestión.
3. Componentes seguros escapando siempre las salidas HTML para evitar XSS.

---

### FASE 8: Dockerización y Despliegue (Opcional)
**Objetivo:** Preparar la aplicación para un entorno de producción (Gunicorn, Nginx, Docker).

---

## Verificación
Iremos comprobando paso a paso:
1. Verificaremos el inicio del servidor en cada fase.
2. Haremos pruebas de inserción en la base de datos tras las migraciones.
3. Validaremos visualmente la interfaz de usuario.
