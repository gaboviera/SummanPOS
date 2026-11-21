# GEMINI.md

This file provides guidance to Google Antigravity and Gemini Code Assist when working with code in this repository.

> **Idioma:** Responder siempre en español.

> **CRITICAL — Cross-Agent Instruction Sync Rule:**
> When any AI agent (Claude, Gemini, Codex/Copilot, DeepSeek) updates or modifies this instruction file, it **MUST** synchronize and apply those changes across all sibling instruction files (`CLAUDE.md`, `GEMINI.md`, `AGENTS.md`, `DEEPSEEK.md`) in this directory to maintain unified instructions.

## Aprendizajes del Agente (Mejora Continua)

> **INSTRUCCIÓN CRÍTICA — LEER PRIMERO:** Esta sección es tu memoria persistente de mejora continua. **Con cada ciclo de ejecución** (al completar una tarea, resolver un error, descubrir un patrón, o ajustar un flujo) **y con cada actualización de cualquier Markdown** (directivas, CLAUDE.md, AGENTS.md, GEMINI.md, READMEs de scripts), **debes agregar aquí un aprendizaje nuevo** si surgió algo no trivial. El objetivo es que este archivo se vuelva más útil y preciso con el tiempo, acumulando conocimiento del proyecto que no se pierde entre sesiones.
>
> **Qué registrar:** restricciones de APIs descubiertas, rate limits reales, patrones que funcionan, errores que se repiten, decisiones de diseño tomadas con el usuario, supuestos que resultaron falsos, atajos útiles, gotchas del entorno.
>
> **Qué NO registrar:** detalles efímeros de una sola tarea, información ya documentada en la directiva correspondiente, aprendizajes propios de un flujo que tiene (o debería tener) directiva — esos van en la sección *Historial de aprendizajes* de esa directiva, cosas triviales derivables del código.
>
> **Formato de cada aprendizaje:**
> ```
> - **YYYY-MM-DD — [Tema corto]:** Descripción del aprendizaje en 1-3 líneas. **Por qué importa:** consecuencia práctica o cómo aplicarlo en el futuro.
> ```
>
> **Higiene:** si un aprendizaje queda obsoleto o se contradice con otro más reciente, actualízalo o elimínalo en vez de acumular ruido. Mantén la lista ordenada por fecha (más recientes arriba). Si superas ~25 entradas, consolida las más antiguas o promuévelas a la directiva que corresponda.

### Registro de aprendizajes

- **2026-09-25 — [Directivas vacías por regla contradictoria]:** `directives/` quedó solo con README en todos los repos porque la regla exigía leer/actualizar directivas pero prohibía crearlas sin permiso, y los aprendizajes se desviaban a esta sección. **Por qué importa:** crear directivas ahora es obligatorio (ver principio 4); los aprendizajes de un flujo concreto van al historial de su directiva, y esta sección queda para conocimiento transversal.
- **2026-09-20 — [Chromium Paged Media Overflow y Viewport Cropping]:** En compilaciones PDF vía Playwright/Chromium, capturas de pantalla de tablas con alturas mayores a 2000px dentro de contenedores con `break-inside: avoid` exceden la altura útil de página A4 (~980px), forzando a Chromium a empujar la imagen y dejar títulos huérfanos en páginas en blanco. **Por qué importa:** limitar en CSS `max-height: 420px; object-fit: contain;` y normalizar capturas a viewport panorámico estándar (1650x1050px) garantiza imágenes nítidas a ancho completo, elimina páginas en blanco y previene rebanados indeseados.
- **2026-09-20 — [Playwright MCP Roots y Base64 PDF Rendering]:** Playwright MCP restringe el guardado de capturas a su raíz de ejecución (`.playwright-mcp`), fallando al intentar guardar en rutas externas arbitrarias. Asimismo, la compilación de PDFs editoriales vía `page.pdf()` es instantánea y determinista al incrustar imágenes como URIs Base64 en el HTML maestro. **Por qué importa:** guardar las capturas en la raíz de Playwright y sincronizarlas mediante Python a `docs/` evita errores de permisos, y el patrón Base64 previene bloqueos de CORS o lecturas locales en Chromium.
- **2026-09-16 — [Custom Agents y Paralelización en Antigravity]:** La ejecución secuencial en un único contexto de tareas independientes (análisis multi-repo, backend/frontend, auditorías) ralentiza el avance y agota la ventana de contexto. **Por qué importa:** delegar subtareas concurrentes vía `invoke_subagent` con múltiples entradas en `Subagents` o apoyándose en el agente `orchestrator` aprovecha el paralelismo nativo y el reactive wakeup sin necesidad de polling.
- **2026-09-16 — [Revisión y Uso Proactivo de Skills y Subagentes]:** Realizar tareas complejas en un solo contexto saturando el hilo del modelo líder degrada la precisión y omite buenas prácticas especializadas. **Por qué importa:** el agente debe consultar primero el catálogo de skills y agentes disponibles (seguridad, testing, research, arquitectura) y delegarles tareas modulares para mantener alta especialización y fidelidad.
- **2026-09-16 — [Windows PowerShell Multiline Quotes]:** En Windows PowerShell, pasar cadenas multilínea complejas con comillas y markdown en comandos inline `-Command "..."` genera errores de parseo y sintaxis (`CommandNotFoundException`). **Por qué importa:** siempre escribir scripts auxiliares o de sincronización a archivos `.py` dedicados en `scratch/` o `agents_scripts/` y ejecutarlos vía `python <script>.py` para garantizar determinismo y reproducibilidad.
- **2026-09-16 — [Aislamiento de Directrices MCP por Repositorio]:** Duplicar la tabla global completa de herramientas MCP en cada submódulo añade ruido y acoplamiento innecesario. **Por qué importa:** cada repositorio git debe documentar exclusivamente sus herramientas MCP en su sección 2, reservando la matriz global exhaustiva solo para la raíz del workspace.
- **2026-09-13 — [Cross-Agent Sync Rule en 4 Agentes]:** Las directivas y aprendizajes divergen si no se sincronizan de forma atómica en CLAUDE.md, GEMINI.md, AGENTS.md y DEEPSEEK.md. **Por qué importa:** toda modificación a partir de la línea 4 debe ser estrictamente idéntica en los cuatro archivos hermanos para preservar la memoria persistente en cualquier entorno o modelo.
- **2026-09-10 — [Resolución de Módulos ESM y Context7 en Windows]:** El servidor MCP Context7 requiere empaquetado Node compatible y ejecución npx sin dependencias rotas de Zod en ES Modules. **Por qué importa:** verificar y empaquetar herramientas MCP con scripts deterministas testeados antes de referenciarlas en la configuración global.

- **2026-09-25 — [Registro de Servidores MCP Remotos HTTP/SSE en Antigravity]:** Para conectar endpoints MCP remotos (como Higgsfield en `https://mcp.higgsfield.ai/mcp`), se debe configurar `serverUrl`/`url` en `~/.gemini/antigravity/mcp_config.json`, `~/.gemini/config/mcp_config.json`, `~/.gemini/settings.json` y el `.mcp.json` del proyecto. Adicionalmente, Antigravity requiere que sus esquemas de herramientas y directivas residan en `~/.gemini/antigravity/mcp/<serverName>/` para exponerlos en `<mcp_servers>` y resolver llamadas `call_mcp_tool`. **Por qué importa:** sin la carpeta de esquemas JSON en `~/.gemini/antigravity/mcp/`, Antigravity no expone las herramientas lazy ni genera el contexto de invocación para el modelo.
<!-- Agrega nuevas entradas arriba de esta línea. -->

---

Tú operas dentro de una arquitectura de 3 capas que separa responsabilidades para maximizar la confiabilidad. Los LLMs son probabilísticos, mientras que la mayoría de la lógica de negocio es determinista y requiere consistencia. Este sistema resuelve esa incompatibilidad.

## La Arquitectura de 3 Capas

**Capa 1: Directiva (Qué hacer)**
- Básicamente son SOPs escritos en Markdown, ubicados en `directives/`
- Definen los objetivos, entradas, herramientas/scripts a usar, salidas y casos extremos
- Instrucciones en lenguaje natural, como las que le daría a un empleado de nivel medio

**Capa 2: Orquestación (Toma de decisiones)**
- Esta es tu función. Tu trabajo: enrutamiento inteligente.
- Leer directivas, llamar herramientas de ejecución en el orden correcto, manejar errores, pedir aclaraciones, actualizar directivas con los aprendizajes
- Tú eres el puente entre la intención y la ejecución. Por ejemplo, no improvises un commit: busca el flujo en el índice de `directives/README.md`, lee `directives/commit_y_push.md` y ejecuta `scripts/scan_secrets.py --staged` tal como indica. Lo mismo aplica a despliegues, migraciones o cualquier flujo que tenga directiva

**Capa 3: Ejecución (Hacer el trabajo)**
- Scripts de Python deterministas en `agents_scripts/` (importante no usar variables sensibles hardcodeadas, usa `.env`)
- Variables de entorno, tokens de API, etc. se almacenan en `.env`
- Manejan llamadas a APIs, procesamiento de datos, operaciones de archivos e interacciones con bases de datos
- Confiables, testeables, rápidos. Usa scripts en vez de trabajo manual.

**Por qué funciona esto:** si tú haces todo por tu cuenta, los errores se acumulan. Un 90% de precisión por paso = 59% de éxito en 5 pasos. La solución es empujar la complejidad hacia código determinista. Así tú te concentras solo en la toma de decisiones.

## Principios de Operación

**1. Revise primero si existen herramientas**
Antes de escribir un script, revisa `agents_scripts/` según tu directiva. Solo crea scripts nuevos si no existe ninguno.

**2. Revise y use proactivamente Skills y Agentes especializados**
- Antes de iniciar cualquier tarea técnica compleja (auditorías de seguridad, creación o ejecución de pruebas, refactorizaciones, investigación profunda de código, diseño de UI o debugging), consulta el inventario de **skills** y **subagentes** disponibles en el entorno (`.claude/skills/`, `.agents/skills/`, `.codex/skills/` y los roles en `.claude/agents/`, `.agents/agents/`).
- Si existe una herramienta, skill o subagente especializado (ej. `security-auditor` para escaneo de secretos y credenciales, `research` o `code-explorer` para navegación profunda, `test-driven-development` para flujos TDD, `systematic-debugging` para rastreo de fallos, `fable-foreman` para coordinación multi-tarea), **debes invocarlo o apoyarte en él** en lugar de ejecutar acciones a ciegas o de forma manual.
- No intentes resolver en un único contexto lineal tareas que demandan verificación especializada e independiente.

**3. Auto-corrección cuando algo falla**
- Lee el mensaje de error y el stack trace
- Corrige el script y pruébalo de nuevo (a menos que use tokens/créditos de pago—en ese caso consulta primero con el usuario)
- Actualiza la directiva con lo que aprendiste (límites o rate limits de API, tiempos, casos extremos)
- Ejemplo: si llegas al rate limit de una API → investigas la API → encuentras un endpoint batch que soluciona el problema → reescribes el script → pruebas → actualizas la directiva.

**4. Actualice las directivas a medida que aprende**
Las directivas son documentos vivos. Cuando descubras restricciones de API, mejores enfoques, errores comunes o expectativas de tiempo—actualiza la directiva. **Crear** una directiva es obligatorio y no requiere permiso cuando: (a) completas un flujo de varios pasos que probablemente se repita, (b) agregas un script en `agents_scripts/` o `scripts/` que ninguna directiva referencia, o (c) ejecutaste una tarea para la que no existía directiva. Regístrala en el índice de `directives/README.md` en el mismo commit. **Reescribir o eliminar** una directiva existente (cambiar su objetivo o su flujo principal) sí requiere confirmación del usuario; agregar aprendizajes a su historial no. Las directivas son tu conjunto de instrucciones y deben preservarse (y mejorarse con el tiempo, no usarse de manera improvisada y luego descartarse).

## Ciclo de Auto-corrección

Los errores son oportunidades de aprendizaje. Cuando algo falla:
1. Corrija el problema
2. Actualice la herramienta
3. Pruebe la herramienta, asegúrese de que funcione
4. Actualice la directiva con el nuevo flujo
5. El sistema ahora es más robusto

## Organización de Archivos

**Estructura de directorios:**
- `.tmp/` - Todos los archivos intermedios (dossiers, datos scrapeados, exportaciones temporales). Nunca se suben al repositorio, siempre se regeneran.
- `agents_scripts/` - Scripts de Python (las herramientas deterministas).
- `directives/` - SOPs en Markdown (el conjunto de instrucciones).
- `.env` - Variables de entorno y claves de API.
- `credentials.json`, `token.json` - Credenciales de OAuth de Google (solo cuando el flujo los requiera; en `.gitignore`).

**Principio clave:** Los archivos intermedios viven en `.tmp/` y pueden borrarse siempre. Cualquier salida del flujo debe ser reproducible ejecutando el flujo de nuevo, nunca editada a mano.

## Resumen

Tú estás entre la intención humana (directivas) y la ejecución determinista (scripts de Python). Lee instrucciones, apóyate proactivamente en los skills y agentes especializados disponibles, toma decisiones, llama herramientas, maneja errores y mejora el sistema continuamente.

Sé pragmático. Sé confiable. Auto-corrígete.

---

## Google Antigravity & Gemini: Custom Agents, Orquestador y Paralelización

Google Antigravity cuenta con soporte nativo para **Custom Subagents** definidos declarativamente (`.agents/agents/*.md`, `~/.gemini/config/agents/*.md`) o dinámicamente mediante herramientas del sistema (`define_subagent`, `invoke_subagent`, `manage_subagents`):

1. **Agente Orquestador (`orchestrator`):**
   - Definido globalmente (`~/.gemini/config/agents/orchestrator.md`) y localmente en `.agents/agents/orchestrator.md`.
   - Función principal: Descomponer objetivos amplios en subtareas modulares, delegar en subagentes especializados, coordinar la ejecución paralela y consolidar los entregables finales con verificación determinista.
2. **Paralelización de Tareas:**
   - Despachar múltiples subagentes concurrentes en una única llamada a `invoke_subagent` (pasando varios elementos en el array `Subagents`), lo que permite que se ejecuten en paralelo en segundo plano sin saturar el contexto principal:
     ```json
     {
       "Subagents": [
         {
           "TypeName": "research",
           "Role": "Backend Code Explorer",
           "Prompt": "Analizar controladores y rutas de autenticación en server/..."
         },
         {
           "TypeName": "research",
           "Role": "Frontend UI Explorer",
           "Prompt": "Analizar componentes de formularios y estado en src/..."
         },
         {
           "TypeName": "security-auditor",
           "Role": "Credentials Auditor",
           "Prompt": "Auditar agents_scripts y .env para verificar Zero-Plaintext-Credentials..."
         }
       ]
     }
     ```
3. **Creación de Agentes Especializados bajo Demanda:**
   - Cuando una tarea requiera habilidades o herramientas específicas que no cubran los roles existentes, el agente puede crear nuevos agentes dinámicamente usando `define_subagent` asignando permisos de escritura, herramientas de subagente y herramientas MCP.
4. **Regla de Cero Polling (Reactive Wakeup):**
   - Tras lanzar subagentes o tareas en segundo plano, NUNCA ejecutar bucles de espera (`sleep` o loops de `manage_task/status`). El bus de mensajería reactivo de Antigravity despierta automáticamente el turno del modelo al recibir respuestas o finalizar tareas.

---

## What this repository is: SummanPOS (Flask POS & Inventory System)

POS and Inventory management system for retail and wholesale operations.

- Active application: `flask_iventario/` is the live application; `flask_api/` is an older split.
- Database: PostgreSQL with SQLAlchemy models and Alembic migrations via Flask-Migrate.
- **Migration Rule (Enforced by CI):** If you touch a SQLAlchemy model, you MUST generate and commit an Alembic migration in the same change:
  ```bash
  flask db migrate -m "Description of change"
  ```
- `check_migrations.yml` runs on push/PR to `dev` and `main`. It fails if a model change is unmigrated.
- Never call `db.create_all()` in application code; schema is derived purely from migrations.
- DB operations run via workflow `db_migrations.yml` (`current`, `upgrade`, `rollback`, `stamp --purge`).
- Deployments use `rsync --delete` to prevent stale migration files.



---

## Agents Scripts & Security Policy (`agents_scripts/` & `security-secret-scanner`)

When creating scripts for diagnostics, database inspections, one-off fixes, or testing:

1. **Where to create agent scripts:**
   - Always in `agents_scripts/<script_name>.py` (or `.sh`, `.js`).
   - This directory keeps agent-generated scripts strictly separated from core development (`desarrollo`).
   - **Never in the repository root**. The root must remain clean.
   - Scripts in `agents_scripts/` are tracked in Git for team collaboration, but **must strictly adhere to the Zero-Plaintext-Credentials Rule**. Real `.env` files and caches inside `agents_scripts/` are gitignored.
2. **How to execute agent scripts:**
   ```bash
   python agents_scripts/<script_name>.py
   ```
3. **Where permanent repo scripts belong:**
   - Permanent, shared tooling and production utilities belong directly in `scripts/`.
4. **Zero-Plaintext-Credentials Rule (MANDATORY):**
   - **NEVER hardcode production passwords, tokens, API keys, or private keys** in any script or codebase.
   - All scripts must consume credentials via `os.environ` or `.env` (refer to `agents_scripts/.env.example`).
5. **Pre-Commit Secret Scanning (All Agents):**
   - Before committing, submitting a PR, or finishing changes, every agent MUST verify that no secrets exist:
     ```bash
     python scripts/scan_secrets.py --staged
     ```
   - To audit all agent scripts in the repository:
     ```bash
     python scripts/scan_secrets.py
     ```
6. **Git Pre-Commit Hook:**
   - Every repository has an automated pre-commit hook installer (`python scripts/install_hooks.py`) ensuring commits with plaintext credentials are automatically blocked.
7. **Specialized Agent & Skill:**
   - The `security-auditor` agent and `security-secret-scanner` skill are globally available across Antigravity, Claude, OpenAI/Codex, and DeepSeek to audit files, verify `.gitignore`, and sanitize secrets.
8. **CI/CD Automated Security Scanning (GitHub Actions):**
   - Every push and pull request is automatically audited via `.github/workflows/security.yml` using the reusable workflow `SummanTech/infra-templates/.github/workflows/security-scan.yml`.
   - Combines **Aqua Security Trivy** (filesystem secrets, misconfigurations, and CVEs), **TruffleHog OSS** (git history and verified credentials scanner), and the **SummanTech Custom Scanner** (`python scripts/scan_secrets.py --all`).


## Model Context Protocol (MCP) Integration: Playwright & Context7

Este workspace y todos sus repositorios cuentan con integración nativa del **Model Context Protocol (MCP)** mediante configuración global en Claude Code (`~/.claude.json`), Google Antigravity (`~/.gemini/config/mcp_config.json`) y configuración declarativa local (`.mcp.json`).

### 1. Servidores MCP Instalados y Configuración

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

- **Playwright MCP (`@playwright/mcp`)** ([documentación oficial](https://playwright.dev/docs/getting-started-mcp)):
  - Control de navegador real en vivo basado en el **Accessibility Tree** (evita adivinación por píxeles y opera mediante selectores semánticos y refs accesibles).
  - Capacidades: Navegación interactiva, llenado de formularios, clics, emulación de dispositivos (`--device "iPhone 15"` o `--mobile`), captura de snapshots del DOM y monitoreo de errores de consola (`--console-level error`).
- **Context7 MCP (`@upstash/context7-mcp`)** ([documentación oficial](https://context7.com)):
  - Inyección en tiempo real de **documentación oficial y snippets de código actualizados** y específicos por versión para librerías y frameworks.
  - Elimina alucinaciones de APIs inexistentes o patrones obsoletos en modelos de IA. Se invoca automáticamente cuando el agente detecta la necesidad o explícitamente en el prompt (`use context7`).

### 2. Directrices de Uso en este Repositorio

| Repositorio / Dominio | Uso de Playwright MCP (`@playwright/mcp`) | Uso de Context7 MCP (`@upstash/context7-mcp`) |
| :--- | :--- | :--- |
| **`SummanPOS/`** (Punto de venta e inventario) | Validar flujos de caja, navegación de inventario, interacción de inputs numéricos y consistencia de UI en `flask_iventario/`. | Consultar sintaxis de Flask 3, SQLAlchemy 2, Flask-Migrate y extensiones de Python. |
### 3. Reglas de Seguridad y Cero Credenciales (MANDATORIO)
- **Zero-Plaintext-Credentials:** NUNCA incluir llaves de API (`CONTEXT7_API_KEY`, etc.) ni credenciales dentro de archivos versionados (`.mcp.json`). Cualquier credencial debe consumirse desde variables de entorno locales o secretos de CI.
- **Entornos de Ejecución Seguros:** Playwright debe operar en modo headless por defecto durante tareas automatizadas y nunca realizar acciones destructivas en entornos de producción.

---

## Common Commands & Workflows

```bash
docker-compose up --build   # Run full stack locally
flask db migrate -m "..."   # Generate migration after model change
flask db upgrade            # Apply migrations locally
```

---

## Claude Code Agent Teams & Multi-Agent Orchestration

Claude Code Agent Teams ([documentación oficial](https://code.claude.com/docs/en/agent-teams)) está configurado y habilitado en este repositorio mediante `.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "teammateMode": "in-process"
}
```

- **Modo de ejecución (`teammateMode: "in-process"`):** Todos los compañeros de equipo (`teammates`) se ejecutan en modo en-proceso dentro de la misma terminal o sesión interactiva, garantizando compatibilidad multiplataforma nativa (Windows PowerShell, Linux, macOS) sin requerir gestores externos de paneles (`tmux` o `it2`).
- **Uso de Subagentes como Teammates:** Los roles definidos en `.claude/agents/*.md` (como `security-auditor`) pueden invocarse directamente como miembros especializados del equipo con herramientas y permisos asignados:
  ```text
  Spawn a teammate using the security-auditor agent type to audit agents_scripts/ and verify staged changes.
  ```
- **Capacidades Colaborativas:**
  - Coordinación y comunicación directa inter-agente mediante mensajes.
  - Tablero centralizado de tareas (`TaskList`, `TaskCreate`, `TaskUpdate`) para distribuir trabajo autónomamente.
  - Exploración en paralelo para revisiones de código, pruebas de hipótesis y desarrollo modular desacoplado.

---

## Cross-Repository Platform Architecture Guidelines

- **Branch is the environment**: `main` → `prd`; any other branch (`dev`, `uat`, etc.) → environment folder of same name.
- **Deploy path**: `/opt/deploy/<env>/<app>/` on the VPS.
- **Networking**: Joined to external network `<env>_shared_net`. Reached via container/service name.
- **Runners**: Self-hosted labeled `[self-hosted, "<provider>-<env>"]`.
- **Manual Deploys**: Deployments are `workflow_dispatch` only (push does not deploy).
- **Secrets**: Injected per GitHub Environment via `.env` at deploy time; never commit `.env`.


---

<!-- AGENT-INVENTORY:START -->

## Inventario de Skills y Agentes (bloque gestionado)

> Generado por `agent-inventory`. No editar a mano: se reescribe con
> `python ../agent-inventory/scripts/inventory.py update`. El mismo bloque se mantiene identico
> en `CLAUDE.md`, `GEMINI.md`, `AGENTS.md` y `DEEPSEEK.md`.

- **Ultimo cambio detectado:** `2026-09-22T21:13:26+00:00`
- **Total instalado aqui:** 200 skills, 150 agentes
- **Detalle completo:** [`../agent-inventory/docs/repos/SummanPOS.md`](../agent-inventory/docs/repos/SummanPOS.md)
- **Historial de cambios:** [`../agent-inventory/CHANGELOG.md`](../agent-inventory/CHANGELOG.md)

| Scope | Directorio | Skills | Agentes |
| --- | --- | --- | --- |
| Claude Code | `.claude/` | 99 | 74 |
| Google Antigravity | `.agents/` | 100 | 75 |
| OpenAI Codex | `.codex/` | 1 | 1 |

Sin cambios en el ultimo escaneo.

<!-- AGENT-INVENTORY:END -->
