# Guía de Desarrollo por Fases: Arquitectura Flask Modular

Esta guía detalla el orden lógico y la estructura recomendada para construir y mantener una aplicación web robusta con Flask, utilizando un patrón de arquitectura modular (MVC extendido con Servicios, Blueprints y Scripts de Automatización). Es la estructura base del sistema SummanPOS.

---

## FASE 1: Preparación del Entorno y Dependencias
**Objetivo:** Configurar el entorno de trabajo aislado e instalar las librerías base de Flask y bases de datos.

1. **Crear entorno virtual e instalar dependencias:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Mac/Linux o Git Bash
   .venv\Scripts\activate     # Windows CMD/PowerShell
   
   pip install Flask Flask-SQLAlchemy Flask-Migrate python-dotenv Flask-Login bcrypt psycopg2-binary
   ```

2. **Gestión de variables de entorno (`.env`):**
   - Es vital no subir credenciales al control de versiones. Todas las configuraciones (URL de BD, claves secretas, contraseñas de VPS/Docker) deben residir en `.env` (ignorado en `.gitignore`).

---

## FASE 2: Configuración Base y Extensiones
**Objetivo:** Configurar las extensiones principales fuera del archivo `app.py` para evitar dependencias circulares.

1. **`extensions.py`:**
   - Instanciar herramientas globales (`db`, `migrate`, `login_manager`) sin atarlas directamente a la `app`.
2. **`app.py` (Fábrica de Aplicaciones):**
   - Cargar variables del `.env`.
   - Inicializar extensiones (`db.init_app(app)`).
   - Registrar Blueprints (Rutas).

---

## FASE 3: Definición de Modelos (Capa de Datos)
**Objetivo:** Traducir las entidades del dominio a tablas en la base de datos (PostgreSQL/SQLite).

1. **`models.py`:**
   - Centralizar entidades. Ej: usar un único modelo `Contactos` para agrupar Clientes y Proveedores.
   - **Tipos de Datos Críticos:** Usar `DateTime` (o `TIMESTAMP`) para fechas que requieran precisión de horas y minutos, en lugar de `Date`.
   - **Soft Delete:** Añadir el campo `deleted_at` para desactivar registros sin romper el historial financiero o inventario.

---

## FASE 4: Capa de Servicios (Lógica de Negocio Central)
**Objetivo:** Aislar reglas de negocio, cálculos y modificaciones a la BD lejos de las rutas web.

1. **Directorio `services/`:**
   - Un archivo por módulo (ej. `ventas_service.py`, `compras_service.py`, `bcv_service.py`).
2. **Control Transaccional (Reversiones):**
   - Los servicios deben ser responsables de operaciones complejas, como **anular transacciones** (revertir stock de órdenes canceladas, generar registros de "SALIDA POR ANULACION") y hacer el `db.session.commit()` o `db.session.rollback()` pertinente de forma segura.

---

## FASE 5: Tareas en Segundo Plano (Cron Jobs y Concurrencia)
**Objetivo:** Ejecutar procesos automatizados (ej. actualizar tasas de cambio) sin bloquear la aplicación.

1. **Scheduler (APScheduler):**
   - Configurar tareas (Jobs) que corren en intervalos.
2. **Control de Concurrencia (Locking):**
   - Si la app corre con múltiples workers (ej. Gunicorn/Docker), usar un mecanismo como `fcntl` para crear un archivo de bloqueo (`scheduler.lock`). Esto asegura que **solo un worker ejecute el cron**, previniendo registros duplicados en la base de datos.
3. **Filtros Anti-Spam:**
   - En los servicios correspondientes, validar el tiempo transcurrido desde la última ejecución (ej. `if tiempo < 300 segundos: return`) para mitigar peticiones duplicadas manuales.

---

## FASE 6: Controladores y Rutas Modulares (Blueprints)
**Objetivo:** Definir Endpoints agrupados lógicamente.

1. **Directorio `routes/`:**
   - Cada funcionalidad tiene su archivo (`auth_routes.py`, `inventario_routes.py`).
   - Crear rutas `GET` (vistas) y `POST` (acciones/APIs).
2. **Protección:** Asegurar rutas críticas con `@login_required` o verificando el rol (Admin/Supervisor).

---

## FASE 7: Interfaz Frontend (UI / UX / Plantillas)
**Objetivo:** Interfaces limpias, reactivas y responsivas.

1. **Directorio `templates/` (Jinja2):**
   - Mantener una plantilla `base.html` con la estructura global y componentes compartidos.
2. **Vistas de Impresión (`@media print`):**
   - Plantillas despojadas de sombras y botones (ej. `recibo.html`) para facilitar la impresión directa en impresoras térmicas (POS).
3. **Punto de Venta (SPA / API Local):**
   - Utilizar peticiones asíncronas (`fetch` a Endpoints REST) en pantallas de ventas/compras para no recargar la página completa, construyendo y renderizando nodos dinámicos al instante.

---

## FASE 8: Contenerización y Despliegue (Docker)
**Objetivo:** Garantizar portabilidad absoluta desde desarrollo hasta producción.

1. **`Dockerfile` y `docker-compose.yml`:**
   - Empaquetar la aplicación en una imagen inmutable.
   - Orquestar la web app (`Gunicorn`) y la base de datos (`PostgreSQL`) junto a sus volúmenes (para retener fotos subidas y los datos de BD).
2. **Directorio `scripts/` (Automatización):**
   - Mantener scripts de operaciones (ej. `deploy_full.py`, `patch_and_migrate.py`) para evitar comandos manuales.
   - **Flujo de Deploy Ideal:**
     1. `git push` (Control de versiones).
     2. Construir (`docker build`) y subir imagen al Registry (`docker push`).
     3. Conexión SSH automatizada al VPS.
     4. Descarga de imagen remota (`docker pull`) y reinicio de contenedores sin perder datos.

---

## Estructura Final del Proyecto

```text
MiProyecto/
├── .env                     # Credenciales (NO SE SUBE AL REPOSITORIO)
├── .gitignore               
├── requirements.txt         # Lista de dependencias (pip freeze)
├── Dockerfile               # Instrucciones para la imagen de producción
├── docker-compose.yml       # Orquestación del entorno
│
├── app.py                   # Inicialización, Schedulers y Blueprints
├── extensions.py            # Instancias de BD, Login, Migrate
├── models.py                # Modelos SQLAlchemy de tablas
│
├── routes/                  # Controladores web (Blueprints)
│   ├── auth_routes.py
│   └── compras_routes.py    
│
├── services/                # Lógica de negocio (Donde ocurre la magia)
│   ├── auth_service.py
│   ├── compras_service.py   # Ej: Lógica de anular órdenes y revertir stock
│   └── bcv_service.py       # Ej: Tareas automatizadas Anti-Spam
│
├── scripts/                 # Scripts de utilidad y Despliegue
│   ├── deploy_full.py       # Build local, push a DockerHub y despliegue por SSH
│   ├── fix_db.py            
│   └── patch_and_migrate.py 
│
├── static/                  # Archivos públicos (CSS, JS, Logos, Uploads)
└── templates/               # Vistas HTML renderizadas por Jinja2
    ├── base.html
    └── compras/
```
