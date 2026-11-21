#!/usr/bin/env python3
"""
Scanner de Secretos y Credenciales Sensibles - SummanTech
Audita archivos en busca de contraseñas, tokens, llaves privadas, IPs y usuarios en texto plano.

Uso:
  python scripts/scan_secrets.py                  # Escanea agents_scripts/ por defecto
  python scripts/scan_secrets.py --all            # Escanea todo el repositorio rastreado por Git
  python scripts/scan_secrets.py --staged         # Escanea unicamente archivos en 'git diff --cached' (para pre-commit)
  python scripts/scan_secrets.py --path <directorio_o_archivo>
"""

import sys
import os
import re
import argparse
import subprocess
from pathlib import Path

IGNORED_EXTENSIONS = {
    ".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".zip", ".tar", ".gz", ".7z", ".pdf", ".woff", ".woff2",
    ".ttf", ".eot", ".bin", ".lock", ".db", ".sqlite", ".md",
    ".tfstate", ".backup"
}

IGNORED_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".pytest_cache", "htmlcov", "dist", "build", "odoo-core",
    "odoo-venezuela", "docs", "tests", "__tests__",
    # Skills de terceros instaladas via 'npx skills add' (vendorizadas, no editamos su
    # codigo). "agent" no tiene punto y por eso necesita entrada explicita aqui; .agents
    # y .claude ya quedaban cubiertos por el filtro de directorios ocultos en
    # scan_directory(), pero --staged/--all no aplicaban ese filtro (ver is_ignored_path).
    "agent", ".agents", ".claude",
}

ALLOWLIST_FILENAMES = {
    ".env.example", "scan_secrets.py", "security-auditor.md", "SKILL.md", "README.md"
}

# 1. Secretos explicitos conocidos del entorno (deben detectarse SIEMPRE, incluso en tests)
KNOWN_SECRETS_PATTERNS = [
    (
        "Known Password (Barquisimeto)",
        re.compile(r"""Barquisimeto\d+""", re.IGNORECASE)
    ),
    (
        "Known Password (TuPasswordSeguro)",
        re.compile(r"""TuPasswordSeguro[A-Za-z0-9!@#$%^&*]*""", re.IGNORECASE)
    ),
    (
        "Known Production VPS IP (207.244.244.168)",
        re.compile(r"""207\.244\.244\.168""")
    ),
    (
        "Known Contabo VPS IP (161.97.178.188)",
        re.compile(r"""161\.97\.178\.188""")
    ),
    (
        "Known DB Password (dcple_dev_secret)",
        re.compile(r"""dcple_dev_secret_\d+""", re.IGNORECASE)
    ),
]

# 2. Patrones genericos de credenciales y datos de infraestructura sensibles
GENERIC_PATTERNS = [
    # Host IP o string hardcodeado en llamadas de conexion SSH/Socket
    (
        "Hardcoded Host in SSH/Client Connect",
        re.compile(r"""\.(?:connect|connect_ssh)\s*\(\s*['"](?!\$|\{|\<|localhost|127\.0\.0\.1)[^'"]+['"]""")
    ),
    # Asignacion de host con IP publica fija (excluyendo versiones y loopback)
    (
        "Hardcoded Public IPv4 Address",
        re.compile(r"""(?<!version['":\s])['"](?!127\.0\.0\.1|0\.0\.0\.0|16\.0|17\.0|18\.0|19\.0)(?:[0-9]{1,3}\.){3}[0-9]{1,3}['"]""")
    ),
    # Asignacion de variables de contrasenas con literales de texto
    (
        "Hardcoded Password Assignment",
        re.compile(r"""(?i)(?:password|passwd|pwd|db_password|vps_password)\s*[:=]\s*['"]([^'"\n]{3,})['"]""")
    ),
    # Fallback con credencial en os.environ.get
    (
        "Hardcoded Fallback in os.environ",
        re.compile(r"""os\.(?:environ\.get|getenv)\s*\(\s*['"][^'"]+['"]\s*,\s*['"]([^'"\n]{3,})['"]\s*\)""")
    ),
    # Argumento CLI con password embebido
    (
        "CLI Password Argument",
        re.compile(r"""--(?:db_password|password|pwd)=['"]?([^'"\s\n]{3,})['"]?""")
    ),
    # Asignacion de Tokens / Claves API / Secretos
    (
        "Hardcoded Token or API Key",
        re.compile(r"""(?i)(?:token|api_key|secret_key|client_secret)\s*[:=]\s*['"]([a-zA-Z0-9_\-\.|:]{12,})['"]""")
    ),
    # Cadenas de conexion con usuario y contrasena embebidos
    (
        "Database Connection String with Credentials",
        re.compile(r"""(?:postgres|postgresql|mysql|mongodb(?:\+srv)?):\/\/[a-zA-Z0-9_\.\-]+:([^@\s\/]+)@""")
    ),
    # Llaves privadas y certificados
    (
        "Private Key or Certificate Header",
        re.compile(r"""-----BEGIN [A-Z ]*PRIVATE KEY-----""")
    ),
]

SAFE_PLACEHOLDERS = {
    "", "none", "null", "false", "true", "admin", "root", "postgres",
    "password", "test", "dummy", "change_me", "example", "your_password",
    "tu_password", "placeholder", "xxx", "vps_host", "vps_user", "vps_password",
    "localhost", "5432", "127.0.0.1", "default_secret", "development", "production",
    "ci-only-secret-not-used-in-any-environment", "123456", "secret", "secret123",
    "..."
}

def is_safe_value(val):
    if not val:
        return True
    v = val.strip().lower()
    if v in SAFE_PLACEHOLDERS:
        return True
    if v.startswith("<") or v.endswith(">"):
        return True
    if v.startswith("$") or v.startswith("{") or v.startswith("%"):
        return True
    if all(c == "." for c in v):
        return True
    return False

def scan_file(filepath):
    findings = []
    path = Path(filepath)

    if not path.is_file():
        return findings

    # Check ignored extensions or names
    if path.suffix.lower() in IGNORED_EXTENSIONS or path.name in ALLOWLIST_FILENAMES:
        return findings

    # Ignore files in test directories or test files for generic checks
    is_test_file = any(part in {"test", "tests", "__tests__", "evals"} for part in path.parts) or path.name.startswith("test_") or path.name.endswith((".test.js", ".test.mjs", ".test.ts", ".test.jsx", ".test.tsx"))

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return [("File Read Error", 0, f"No se pudo leer el archivo: {e}")]

    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        # 1. Secretos conocidos prioritarios (siempre aplican)
        for rule_name, pattern in KNOWN_SECRETS_PATTERNS:
            if pattern.search(line):
                findings.append((rule_name, line_idx, stripped))
                break

        if findings and findings[-1][1] == line_idx:
            continue

        # Skip generic patterns for test files
        if is_test_file:
            continue

        # Skip SQL comments that are documentation/templates
        if stripped.startswith("--") and ("ADMIN_PASSWORD" in stripped or "..." in stripped):
            continue

        # 2. Chequeo generico
        for rule_name, pattern in GENERIC_PATTERNS:
            match = pattern.search(line)
            if match:
                if match.groups():
                    captured = match.group(1)
                    if is_safe_value(captured):
                        continue
                # For IPv4, check if it is part of manifest or version assignment
                if rule_name == "Hardcoded Public IPv4 Address":
                    if "version" in stripped.lower() or "addon" in stripped.lower():
                        continue
                findings.append((rule_name, line_idx, stripped))
                break

    return findings

def get_staged_files():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True
        )
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except Exception as e:
        print(f"[!] Error al obtener archivos en staging: {e}", file=sys.stderr)
        return []

def get_tracked_files(repo_root):
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except Exception:
        return None

def is_ignored_path(rel_path):
    """True si algun componente de la ruta esta en IGNORED_DIRS o es un directorio oculto.

    scan_directory() ya filtraba esto via os.walk, pero --staged y --all (los dos modos
    que realmente se usan: el hook de pre-commit y CI) iteraban archivo por archivo sin
    aplicar ningun filtro de directorio. Esto hacia que IGNORED_DIRS fuera inefectivo en
    la practica para esos dos modos.
    """
    return any(part in IGNORED_DIRS or part.startswith(".") for part in Path(rel_path).parts[:-1])

def scan_directory(target_dir):
    all_findings = {}
    target = Path(target_dir)

    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
        for file in files:
            filepath = Path(root) / file
            findings = scan_file(filepath)
            if findings:
                all_findings[str(filepath)] = findings

    return all_findings

def main():
    parser = argparse.ArgumentParser(description="Escaner de Secretos y Credenciales de SummanTech")
    parser.add_argument("--staged", action="store_true", help="Escanear solo archivos en staging de Git")
    parser.add_argument("--all", action="store_true", help="Escanear todo el repositorio rastreado")
    parser.add_argument("--path", type=str, help="Ruta de archivo o directorio especifico a escanear")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    results = {}

    if args.staged:
        print("[*] Modo Staged: Escaneando archivos staged para el proximo commit...")
        staged = get_staged_files()
        if not staged:
            print("[OK] No hay archivos en staging de Git para escanear.")
            sys.exit(0)
        for rel_path in staged:
            if is_ignored_path(rel_path):
                continue
            abs_path = repo_root / rel_path
            findings = scan_file(abs_path)
            if findings:
                results[str(abs_path)] = findings

    elif args.path:
        target = Path(args.path).resolve()
        print(f"[*] Escaneando ruta especifica: {target}")
        if target.is_file():
            findings = scan_file(target)
            if findings:
                results[str(target)] = findings
        elif target.is_dir():
            results = scan_directory(target)
        else:
            print(f"[!] Error: La ruta {target} no existe.", file=sys.stderr)
            sys.exit(1)

    elif args.all:
        print(f"[*] Escaneando repositorio completo: {repo_root}")
        tracked = get_tracked_files(repo_root)
        if tracked is not None:
            for rel_path in tracked:
                if is_ignored_path(rel_path):
                    continue
                abs_path = repo_root / rel_path
                findings = scan_file(abs_path)
                if findings:
                    results[str(abs_path)] = findings
        else:
            results = scan_directory(repo_root)

    else:
        agents_scripts_dir = repo_root / "agents_scripts"
        print(f"[*] Escaneando agentes y herramientas: {agents_scripts_dir}")
        if agents_scripts_dir.exists():
            results = scan_directory(agents_scripts_dir)
        else:
            print(f"[OK] No existe el directorio {agents_scripts_dir}. Nada que auditar.")
            sys.exit(0)

    # Imprimir reporte
    if results:
        print("\n" + "=" * 70)
        total_issues = sum(len(issues) for issues in results.values())
        print(f"  [ALERTA DE SEGURIDAD CRITICA] Se encontraron {total_issues} posible(s) secreto(s) o dato sensible:")
        print("=" * 70 + "\n")

        for filepath, issues in results.items():
            print(f"[!] Archivo: {filepath}")
            for rule_name, line_num, content in issues:
                print(f"    - Linea {line_num} [{rule_name}]:")
                print(f"       -> {content}")
            print()

        print("-" * 70)
        print("[ERROR] NO SE PERMITE COMITEAR CREDENCIALES, IPS O DATOS SENSIBLES.")
        print("[INFO]  SOLUCION: Parametriza usando 'os.environ.get(...)' o .env (VPS_HOST, VPS_USER, VPS_PASSWORD)")
        print("-" * 70 + "\n")
        sys.exit(1)

    print("\n[OK] Auditoria superada con exito: 0 credenciales o datos sensibles detectados.\n")
    sys.exit(0)

if __name__ == "__main__":
    main()
