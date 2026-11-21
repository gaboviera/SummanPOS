---
name: security-secret-scanner
description: Guía y metodología para auditar, escanear y validar que los scripts en agents_scripts/ y el código del repositorio no contengan credenciales sensibles hardcodeadas (contraseñas, tokens, API keys, llaves privadas, IPs de host o usuarios fijos), asegurando que se utilicen variables de entorno (.env / os.environ) antes de realizar commits o pushes a Git.
---

# Security Secret Scanner Skill

Esta habilidad guía a los agentes y desarrolladores para auditar scripts y cambios antes de subirlos a Git, garantizando que el repositorio permanezca 100% libre de credenciales sensibles y datos de infraestructura de producción.

---

## 🎯 Regla Fundamental

> **NUNCA se debe comitear una credencial, IP pública o usuario en texto plano.**
> Toda conexión a VPS, base de datos, API externa o servicio autenticado debe parametrizarse mediante variables de entorno (`os.environ`) o archivos locales `.env` (los cuales deben estar estrictamente en `.gitignore`).

---

## 🔍 Patrones a Detectar (Expresiones Regulares)

Al auditar scripts (`*.py`, `*.sh`, `*.js`, `*.yml`, etc.), buscar:

1. **Hosts e IPs Públicas en Llamadas de Conexión:**
   * `\.(?:connect|connect_ssh)\s*\(\s*['"][^'"]+['"]` (detectar IPs o strings fijas en vez de variables)
   * `(?!127\.0\.0\.1|0\.0\.0\.0)(?:[0-9]{1,3}\.){3}[0-9]{1,3}` (direcciones IPv4 públicas hardcodeadas)
   * `username\s*=\s*['"][^'"]+['"]` (usuarios como `root` hardcodeados)
2. **Asignación explícita de contraseñas:**
   * `password\s*=\s*['"][^'"]{4,}['"]` (ignorando placeholders como `os.environ.get(...)`)
   * `passwd\s*=`, `pwd\s*=`, `db_password\s*=`
3. **Tokens y Secretos de API:**
   * `token\s*=\s*['"][^'"]+['"]`
   * `api_key\s*=\s*['"][^'"]+['"]`
   * `secret(_key)?\s*=\s*['"][^'"]+['"]`
4. **Cadenas de Conexión con Credenciales Embebidas:**
   * `postgres://.*:.*@` o `postgresql://.*:.*@`
   * `mongodb(\+srv)?://.*:.*@`
   * `mysql://.*:.*@`
5. **Secretos e IPs Conocidas del Entorno:**
   * `Barquisimeto\d+`
   * `TuPasswordSeguro.*`
   * `207\.244\.244\.168`, `161\.97\.178\.188`
6. **Llaves Privadas y Certificados:**
   * `-----BEGIN (RSA|OPENSSH|EC|DSA)? PRIVATE KEY-----`

---

## 🛠️ Procedimiento de Auditoría Paso a Paso

### Paso 1: Identificar Archivos a Revisar
* Si se audita el repositorio completo: revisar todos los scripts en `agents_scripts/` y archivos modificados.
* Si se audita previo a un commit: ejecutar `git diff --cached --name-only` para inspeccionar únicamente los archivos en staging.

### Paso 2: Escanear en Busca de Secretos
* Usar `grep_search` o el script utilitario `python scripts/scan_secrets.py`.
* Si se encuentra una credencial fija, **detener el flujo y advertir al usuario**.

### Paso 3: Refactorizar al Patrón Seguro (`os.environ`)
Reemplazar cualquier conexión dura por:
```python
import os

vps_host = os.environ.get('VPS_HOST')
vps_user = os.environ.get('VPS_USER', 'root')
vps_password = os.environ.get('VPS_PASSWORD')

if not vps_host or not vps_password:
    raise ValueError("Faltan variables de entorno requeridas ('VPS_HOST', 'VPS_PASSWORD'). Configúralas en .env")

ssh.connect(vps_host, username=vps_user, password=vps_password, timeout=15)
```

### Paso 4: Verificar `.gitignore`
* Confirmar que `.env` y `.env.*` están en `.gitignore` (permitiendo únicamente `.env.example`).
* Confirmar que `git status` no muestra archivos de credenciales staged (`.git-credentials`, `*.pem`, `*.key`).

### Paso 5: Validar Documentación en `agents_scripts/README.md`
* Verificar que el script incluya docstring de cabecera.
* Verificar que el script esté registrado en la tabla de `agents_scripts/README.md`.
