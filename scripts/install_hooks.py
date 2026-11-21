#!/usr/bin/env python3
"""
Instalador de Git Hooks de Seguridad - SummanTech
Instala un hook de pre-commit que bloquea commits que contengan contraseñas o secretos en texto plano.
"""

import sys
import os
from pathlib import Path

# Configurar encoding para Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PRE_COMMIT_SCRIPT = """#!/bin/sh
# Hook de Pre-Commit SummanTech: Escáner de Secretos
# Bloquea el commit si se detectan credenciales o contraseñas en texto plano en los archivos staged.

echo "[*] Ejecutando escáner de secretos previo al commit..."
python scripts/scan_secrets.py --staged

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ ERROR: Commit cancelado por detección de secretos o credenciales en texto plano."
    echo "Por favor elimina las credenciales sensibles o usa variables de entorno (os.environ / .env)."
    exit 1
fi

exit 0
"""

def install_hook(repo_dir=None):
    if repo_dir is None:
        repo_dir = Path(__file__).resolve().parent.parent
    else:
        repo_dir = Path(repo_dir)

    git_dir = repo_dir / ".git"
    if not git_dir.exists():
        print(f"[!] Error: {repo_dir} no es un repositorio de Git válido (falta .git).")
        return False

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    pre_commit_file = hooks_dir / "pre-commit"

    try:
        with open(pre_commit_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(PRE_COMMIT_SCRIPT)

        # Hacerlo ejecutable en sistemas Unix / Git Bash
        try:
            current_mode = os.stat(pre_commit_file).st_mode
            os.chmod(pre_commit_file, current_mode | 0o755)
        except Exception:
            pass

        print(f"[✓] Hook de pre-commit instalado exitosamente en: {pre_commit_file}")
        return True
    except Exception as e:
        print(f"[!] Error al escribir el hook: {e}")
        return False

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    success = install_hook(target)
    sys.exit(0 if success else 1)
