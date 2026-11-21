"""Toma una foto de solo lectura del uso de recursos (CPU, RAM, disco) en el VPS.

Ejecuta únicamente comandos de lectura: uptime, nproc, free, df, docker stats --no-stream,
docker top del contenedor de SummanPOS y top en modo batch. No modifica nada.

Credenciales: VPS_HOST, VPS_USER, VPS_PASSWORD desde variables de entorno o el .env
indicado con --env (por defecto flask_iventario/.env). Nunca se imprimen.

Uso:
    python agents_scripts/metricas_recursos_vps.py --salida .tmp/manual_tecnico/metricas.txt [--filtro summanpos]
"""
import argparse
import os
import sys

import paramiko
from dotenv import load_dotenv

COMANDOS = [
    ("Tiempo encendido y carga promedio", "uptime"),
    ("Núcleos de CPU", "nproc"),
    ("Memoria RAM (MB)", "free -m"),
    ("Disco", "df -h / /var/lib/docker 2>/dev/null | sort -u"),
    ("Contenedores (CPU / RAM / red / disco)",
     "docker stats --no-stream --format 'table {{{{.Name}}}}\\t{{{{.CPUPerc}}}}\\t{{{{.MemUsage}}}}\\t{{{{.MemPerc}}}}\\t{{{{.NetIO}}}}\\t{{{{.BlockIO}}}}\\t{{{{.PIDs}}}}' | grep -Ei 'NAME|{filtro}|postgres|caddy'"),
    ("Procesos dentro del contenedor de la app",
     "c=$(docker ps --format '{{{{.Names}}}}' | grep -Ei '{filtro}' | grep -i inventario | head -1); "
     "echo \"Contenedor: $c\"; docker top \"$c\" -o pid,ppid,pcpu,pmem,rss,etime,args"),
    ("Volumen de archivos subidos",
     "docker system df -v 2>/dev/null | grep -Ei 'VOLUME NAME|inventario_uploads'"),
    ("Top de procesos del servidor", "top -bn1 -o %MEM | head -20"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", required=True)
    ap.add_argument("--env", default=os.path.join(os.path.dirname(__file__), "..", "flask_iventario", ".env"))
    ap.add_argument("--filtro", default="summanpos")
    a = ap.parse_args()
    load_dotenv(a.env)
    host, user, pwd = os.getenv("VPS_HOST"), os.getenv("VPS_USER", "root"), os.getenv("VPS_PASSWORD")
    if not host or not pwd:
        sys.exit("Faltan VPS_HOST / VPS_PASSWORD en el entorno.")
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(host, username=user, password=pwd, timeout=20)
    partes = []
    try:
        for titulo, cmd in COMANDOS:
            _, out, err = cli.exec_command(cmd.format(filtro=a.filtro), timeout=60)
            texto = out.read().decode("utf-8", "replace").strip() or err.read().decode("utf-8", "replace").strip()
            partes.append(f"### {titulo}\n$ {cmd.format(filtro=a.filtro)}\n{texto}\n")
    finally:
        cli.close()
    os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
    with open(a.salida, "w", encoding="utf-8") as f:
        f.write("\n".join(partes))
    print("OK ->", a.salida)


if __name__ == "__main__":
    main()
