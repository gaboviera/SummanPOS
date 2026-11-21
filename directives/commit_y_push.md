# Commit y push seguro

**Objetivo:** llevar cambios a GitHub sin exponer credenciales y sin desalinear la documentación multi-agente.
**Cuándo usarla:** antes de cualquier `git commit` / `git push` en este repositorio, hecho por un agente o por una persona.

## Entradas
- Cambios en el working tree de este repositorio (confirmar con `git status` que estás en el repo correcto: el directorio padre `SummanTech/` **no** es un repo git).
- Rama actual: la rama es el entorno (`main` → `prd`; `dev`, `uat`, `19.0-dev`, … → entorno homónimo). Un push **no despliega**; los deploys son `workflow_dispatch` manuales.

## Herramientas
- `scripts/scan_secrets.py` — escáner de credenciales (`--staged`, `--all`, `--path <ruta>`).
- `scripts/install_hooks.py` — instala el hook `pre-commit` que ejecuta el escáner.
- `../agent-inventory/scripts/inventory.py` — lo invoca el hook cuando el commit toca `.claude/`, `.agents/` o `.codex/`.
- `.github/workflows/security.yml` — CI (Trivy + TruffleHog + escáner propio) en cada push/PR.

## Pasos
1. Verifica que el hook esté instalado: si `.git/hooks/pre-commit` no existe o no invoca `scan_secrets.py`, ejecuta `python scripts/install_hooks.py`.
2. Si modificaste `CLAUDE.md`, `GEMINI.md`, `AGENTS.md` o `DEEPSEEK.md`, aplica el mismo cambio en los cuatro (regla de sincronización cross-agent). No edites a mano el bloque gestionado por `agent-inventory`.
3. Si agregaste un script en `agents_scripts/` o `scripts/`, confirma que alguna directiva de `directives/` lo referencia; si no, créala (ver `directives/README.md`).
4. `git add <archivos concretos>` — nunca `.env`, `credentials.json`, `token.json` ni archivos de `.tmp/`.
5. `python scripts/scan_secrets.py --staged` — debe terminar con código 0.
6. `git commit -m "<tipo>: <descripción>"` con tipos convencionales (`feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`).
7. `git push` (con `-u origin <rama>` si la rama es nueva).

## Salidas
- Commit en la rama remota; el workflow `security.yml` corre automáticamente — revisar su resultado.

## Casos extremos y errores conocidos
- **El hook bloquea el commit:** hay una credencial en texto plano. Muévela a `.env` / `os.environ` (ver `agents_scripts/.env.example` si existe) y vuelve a stagear. Si la credencial ya llegó a un commit previo, hay que rotarla: el historial de git la conserva.
- **Commits masivos multi-repo que tocan `.claude/`/`.agents/`:** el hook ejecuta `inventory.py update`, que recalcula hashes de miles de archivos (2-3 min por repo). Si el inventario ya se actualizó en esta misma operación, corre `scan_secrets.py --staged` explícitamente y luego `git commit --no-verify`. Nunca uses `--no-verify` sin ese escaneo manual previo.
- **Scripts auxiliares en Windows PowerShell:** cadenas multilínea con comillas en `-Command "..."` fallan al parsear; escribe el script en `agents_scripts/` (o en un directorio temporal) y ejecútalo con `python`.

## Historial de aprendizajes
- 2026-09-25 — Directiva creada a partir de las reglas dispersas en `CLAUDE.md` (Zero-Plaintext-Credentials, hooks y commits masivos).
