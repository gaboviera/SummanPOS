"""
deploy_full.py
==============
Flujo completo de despliegue:
  1. Build de la imagen Docker localmente
  2. Push al DockerHub
  3. SSH al VPS → pull de la nueva imagen → restart del contenedor

Las credenciales se leen del .env local (protegido por .gitignore).
"""

import os
import subprocess
import sys
import paramiko
from dotenv import load_dotenv

load_dotenv()

# ── Credenciales desde .env ──────────────────────────────────────────────────
DOCKER_USERNAME = os.getenv('DOCKER_USERNAME')
DOCKER_PASSWORD = os.getenv('DOCKER_PASSWORD')
DOCKER_IMAGE    = os.getenv('DOCKER_IMAGE', f'{DOCKER_USERNAME}/flask-inventario')
VPS_HOST        = os.getenv('VPS_HOST')
VPS_USER        = os.getenv('VPS_USER')
VPS_PASSWORD    = os.getenv('VPS_PASSWORD')

CONTAINER_NAME  = 'inventario_app'

def run_local(cmd, check=True):
    """Ejecuta un comando en la terminal local y muestra la salida en tiempo real."""
    print(f"\n> {cmd}")
    result = subprocess.run(cmd, shell=True, text=True)
    if check and result.returncode != 0:
        print(f"X El comando fallo con codigo {result.returncode}")
        sys.exit(1)
    return result

def run_remote(ssh, cmd):
    """Ejecuta un comando SSH y espera su resultado."""
    print(f"\n[VPS] > {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(f"      {out}")
    if err:
        # Filtramos mensajes INFO que no son errores reales
        for line in err.splitlines():
            if not line.startswith('INFO'):
                print(f"[ERR] {line}")
    return exit_status

def step_build():
    print("\n" + "="*55)
    print("  PASO 1: Build de la imagen Docker")
    print("="*55)
    run_local(f"docker build -t {DOCKER_IMAGE}:latest .")

def step_push():
    print("\n" + "="*55)
    print("  PASO 2: Login y Push al DockerHub")
    print("="*55)
    # Login usando stdin directamente con subprocess para evitar espacios en Windows CMD
    print("> docker login -u gabrielviera2000 --password-stdin")
    result = subprocess.run(
        ["docker", "login", "-u", DOCKER_USERNAME, "--password-stdin"],
        input=DOCKER_PASSWORD,
        text=True
    )
    if result.returncode != 0:
        print(f"X El comando fallo con codigo {result.returncode}")
        sys.exit(1)
        
    run_local(f"docker push {DOCKER_IMAGE}:latest")
    print("\n[OK] Imagen publicada exitosamente en DockerHub.")

def step_deploy_vps():
    print("\n" + "="*55)
    print("  PASO 3: Actualizar contenedor en el VPS")
    print("="*55)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"\nConectando a {VPS_HOST}...")
    ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD)
    print("[OK] Conectado.")

    commands = [
        ("Descargando nueva imagen del DockerHub",
         f"docker pull {DOCKER_IMAGE}:latest"),

        ("Reiniciando el contenedor con la nueva imagen",
         f"docker stop {CONTAINER_NAME} && docker rm {CONTAINER_NAME}"),

        ("Levantando contenedor actualizado con docker-compose",
         "cd /opt/deploy && docker-compose up -d inventario_app"),
    ]

    for desc, cmd in commands:
        print(f"\n-> {desc}...")
        status = run_remote(ssh, cmd)
        if status != 0 and 'docker-compose up' not in cmd:
            print(f"  ! Comando retorno codigo {status}, continuando...")

    ssh.close()
    print("\n[OK] VPS actualizado y contenedor reiniciado con la imagen mas reciente.")

def main():
    print("\n*** SummanPOS -- Deploy Completo ***")
    print(f"   Imagen : {DOCKER_IMAGE}:latest")
    print(f"   Servidor: {VPS_HOST}")

    step_build()
    step_push()
    step_deploy_vps()

    print("\n" + "="*55)
    print("  [OK] DEPLOY COMPLETADO EXITOSAMENTE")
    print("="*55 + "\n")

if __name__ == '__main__':
    main()
