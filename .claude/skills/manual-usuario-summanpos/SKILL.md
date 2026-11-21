---
name: manual-usuario-summanpos
description: Genera o actualiza el Manual de Usuario de SummanPOS (un Claude Doc) capturando pantallas automáticamente con Playwright MCP e insertándolas en la sección correcta del manual, sin romper listas ni bloques. Usar cuando pidan crear, actualizar o completar el manual de usuario del sistema, o agregar capturas de pantalla a la documentación.
metadata:
  origin: proyecto
---

# Manual de Usuario SummanPOS — documentación automática con capturas

Automatiza lo que se hizo a mano en la sesión que originó esta skill: navegar la app con
Playwright MCP, tomar capturas de cada pantalla, subirlas al Claude Doc del manual y
colocarlas junto al texto que describe esa pantalla — sin que el motor de docs las meta
como viñetas sueltas dentro de una lista.

## Cuándo usar esta skill

- El usuario pide crear, ampliar o "chequear qué falta" en el Manual de Usuario de SummanPOS.
- Se necesita ilustrar una pantalla nueva del sistema (módulo agregado, formulario cambiado).
- Se va a regenerar el manual completo en PDF/Word después de varios cambios.

## Prerrequisitos

- Playwright MCP conectado (herramientas `mcp__playwright__*`: `browser_navigate`,
  `browser_snapshot`, `browser_click`, `browser_type`/`browser_fill_form`,
  `browser_take_screenshot`). Verificar con `ToolSearch` si no aparecen ya cargadas.
- El servidor de SummanPOS corriendo en local (`docker-compose up --build` o `flask run`),
  normalmente en `http://localhost:5000`. Si no responde, avisar al usuario y no continuar.
- Credenciales de un usuario Administrador **en variables de entorno**, nunca escritas en
  el código, en el chat ni en este archivo — respeta la Zero-Plaintext-Credentials Rule de
  `CLAUDE.md`: `SUMMANPOS_ADMIN_USER`, `SUMMANPOS_ADMIN_PASSWORD`. Si no existen, pedirlas
  al usuario o usar el flujo de credenciales del harness; nunca hardcodear `admin123`.
- El Manual de Usuario ya existe como Claude Doc. Buscarlo con `Artifact(action="list")`
  (o pedirle el link al usuario) antes de crear uno nuevo — nunca duplicar el doc.

## Flujo de trabajo

1. **Confirmar el servidor arriba** (navegar a la URL base con Playwright y comprobar que
   carga, o un `curl`/`Invoke-WebRequest` rápido).
2. **Iniciar sesión una sola vez**:
   - `browser_navigate` a `${BASE_URL}/login`.
   - `browser_snapshot` para obtener los `ref` de los campos usuario/contraseña.
   - Rellenar con las variables de entorno (nunca teclear la contraseña literal en una
     llamada de herramienta que quede visible en el historial si se puede evitar).
   - Click en "Iniciar Sesión" y `browser_snapshot` para confirmar que cayó en `/dashboard`.
3. **Leer el manual vigente primero**: `read` el doc con `projection: outline` y anota qué
   capturas (`alt` de cada `<media>`) ya existen, para no repetir trabajo. Cruza contra la
   tabla de pantallas de abajo y arma la lista de lo que realmente falta.
4. **Por cada pantalla pendiente**:
   a. `browser_navigate` a la URL indicada (o repetir los clics de la columna "Acción" si
      hace falta abrir un modal, cambiar un filtro, etc.).
   b. `browser_snapshot` para confirmar que cargó lo esperado (evita capturar una pantalla
      de error, vacía o con un modal de carga a medias).
   c. `browser_take_screenshot` guardando a un archivo en el scratchpad de la sesión
      (por ejemplo `screens/<slug>.png`).
   d. Subir el archivo al doc: `Artifact(action="upload_asset", url="<url del manual>",
      file_path="<archivo>")` → guarda el `asset id` que devuelve.
   e. Registrar el blob: `create(object="blob", engine="blob", container=C,
      payload={"asset":"<asset id>"})` → devuelve `blob/<blob id>`.
   f. Insertar la imagen en la sección correcta (ver "Cómo insertar sin romper el formato").
5. Al terminar, si el usuario quiere el archivo final, exportar (PDF o Word) y enviarlo con
   `SendUserFile` — ver "Exportar el manual final".

Sube y registra los blobs de varias capturas en paralelo (varias llamadas en el mismo
turno); las inserciones en el doc sí deben ir en llamadas `update` — puedes combinar varias
inserciones independientes en un mismo `payload.ops`.

## Tabla de pantallas del manual (checklist reutilizable)

Ajusta las URLs si cambian las rutas; esta tabla refleja las rutas reales de
`flask_iventario/` a la fecha en que se escribió esta skill.

| Sección del manual | Pantalla | URL o acción | Caption sugerido |
| --- | --- | --- | --- |
| Introducción | Landing | `/` | Página principal del sistema |
| Acceso → Iniciar sesión | Login | `/login` | Pantalla de inicio de sesión |
| Panel principal | Dashboard | `/dashboard` | Panel principal (Resumen Gerencial) |
| Panel principal | Notificaciones | `/notificaciones` | Historial de Notificaciones |
| Ventas → Registrar una venta | POS | `/ventas` (buscar producto, agregar al carrito) | Punto de Venta: búsqueda y carrito |
| Ventas → Registrar una venta | Modal Procesar Venta (contado) | click en "Generar Guía de Despacho" | Modal Procesar Venta: contado |
| Ventas → Registrar una venta | Modal Procesar Venta (crédito) | cambiar Tipo de Venta a Crédito | Modal Procesar Venta: crédito |
| Ventas → Recibo / Factura | Recibo | `/ventas/recibo/<referencia>` | Recibo / Guía de Despacho |
| Ventas → Historial | Historial de Ventas | `/ventas/historial` | Historial de Ventas |
| Inventario → Listado | Panel de Control | `/productos` | Panel de Control de Inventario |
| Inventario → Agregar producto | Nuevo Producto | `/productos/nuevo` | Formulario nuevo producto |
| Inventario → Editar y eliminar | Editar Producto | `/productos/editar/<id>` | Editar un producto |
| Inventario → Editar y eliminar | Papelera | `/productos?eliminados=1` | Papelera de productos eliminados |
| Inventario → Categorías y atributos | Categorías | `/categorias/` | Gestión de Categorías |
| Inventario → Categorías y atributos | Atributos | `/atributos` | Gestión de Atributos |
| Inventario → Listas de Precios | Listas de Precios | `/configuracion/listas-precios` | Gestión de Listas de Precios |
| Inventario → Carga masiva | Importar | `/importar` | Carga Masiva de Inventario |
| Inventario → Control de stock | Transacciones | `/transacciones` | Historial de Movimientos |
| Contactos | Directorio | `/contactos` | Directorio de Contactos |
| Contactos → Datos | Nuevo/Editar Contacto | click en "Nuevo Contacto" desde `/contactos` | Nuevo Contacto |
| Tasas de Cambio | Historial | `/bcv/historial` | Historial de Tasas de Cambio |
| Administración de Usuarios | Usuarios | `/usuarios` | Gestión de Usuarios |
| Administración de Usuarios | Nuevo/Editar Usuario | click en "Nuevo Usuario" desde `/usuarios` | Formulario de usuario |
| Otros módulos → Compras | Órdenes de Compra | `/compras/` | Listado de Órdenes de Compra |
| Otros módulos → Dropshipping | Órdenes de Dropshipping | `/dropshipping` | Listado de Dropshipping |
| Otros módulos → Finanzas | CxC | `/finanzas/cxc` | Cuentas por Cobrar |
| Otros módulos → Finanzas | CxP | `/finanzas/cxp` | Cuentas por Pagar |
| Otros módulos → Configuración de marca | Identidad Corporativa | `/configuracion/marca` | Configuración de marca |

## Cómo insertar sin romper el formato (aprendido a la fuerza en esta sesión)

- **Nunca** uses como ancla un `find` de texto que esté dentro de un `listItem` (una viñeta
  o un paso numerado) para insertar una imagen: el motor de docs la mete como un ítem nuevo
  de esa misma lista, y la imagen termina viéndose como una viñeta o un "5." suelto. En vez
  de eso:
  1. Lee el outline de la sección (`read(..., payload={"projection":"outline"})`, o
     `{"kind":"view","parentId":...}` para una lista puntual) y toma el **id del bloque**
     de la lista completa (`list id='...'`) o del párrafo justo antes de donde va la imagen.
  2. Inserta con `{"op":"insert","target":{"kind":"blocks","ids":["<ese id>"]},"side":"after",
     ...}` — así la imagen queda como párrafo hermano, no anidada dentro de la lista.
- Si algo ya quedó anidado (dentro de una lista o un blockquote), se corrige con `delete`
  (con el `ifHash` del bloque) seguido de un `insert` afuera, o con `move` del bloque a su
  posición correcta — ver `topic.editing` de la skill de docs antes de intentarlo.
- Cuando un texto de anclaje se repite en el documento (`find_ambiguous`), agrega `"nth"`
  según el índice que te devuelve el error, o mejor, usa siempre ids de bloque en vez de
  `find` para evitar el problema de raíz.
- Para reordenar secciones ya escritas, usa `move` con la lista completa de ids de esa
  sección (heading + párrafos + imágenes) en una sola operación, apuntando con `side:"after"`
  a un id estable — no muevas bloque por bloque en llamadas separadas si el orden entre
  ellos importa (el resultado puede quedar intercalado al revés).

## Cómo subir imágenes al doc (secuencia exacta de llamadas)

```
Artifact(action="upload_asset", url="<url del doc>", file_path="<captura local>")
  → devuelve un asset id (32 hex)

create(object="blob", engine="blob", container={"kind":"project","id":"<doc id>"},
       payload={"asset":"<asset id>"})
  → devuelve {"id":"blob/<blob id>"}

update(ref=<body del tab>, engine="prose", container=<doc>, payload={"ops":[
  {"op":"insert","target":{"kind":"blocks","ids":["<id ancla>"]},"side":"after",
   "source":{"as":"markdown","from":{"kind":"inline","content":"![<caption>](blob/<blob id>)"}}}
]})
```

## Exportar el manual final

- PDF: `export(container=doc, file=<tab id>, format="pdf", paper="letter")`.
- Word: igual con `format="docx"`.
- El resultado puede exceder el límite de tokens de la herramienta; en ese caso queda
  guardado en un archivo de resultados. El formato de ese archivo varía (a veces es el JSON
  del tool directo, a veces un array `[{"type":"text","text":"..."}]` con el JSON adentro
  de uno de los elementos) — soporta ambos al decodificar, por ejemplo:

```python
import json, base64

with open(path, "r", encoding="utf-8") as f:
    raw = f.read()

obj = json.loads(raw)
if isinstance(obj, list):
    payload = next(json.loads(item["text"]) for item in obj if item["text"].strip().startswith("{"))
else:
    payload = obj

b64 = payload["data"]["bytes_b64"]
open("salida.pdf", "wb").write(base64.b64decode(b64))
```

- Envía el archivo resultante con `SendUserFile`, nunca solo lo menciones.

## Seguridad y buenas prácticas

- Nunca escribas la contraseña del usuario admin en texto plano en el código, en el chat ni
  en esta skill: léela de variables de entorno, igual que exige la Zero-Plaintext-Credentials
  Rule de `CLAUDE.md`.
- No captures pantallas con datos reales sensibles (cédulas, teléfonos, montos de clientes
  reales) si el manual va a salir de la empresa; preferir datos de prueba cuando se pueda.
- Antes de insertar nada, lee primero el manual vigente para no duplicar capturas que ya
  existen — compara por el texto `alt` de las imágenes ya insertadas, no solo por el nombre
  del archivo.
