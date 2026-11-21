"""Mide CPU, RAM, disco y procesos de los contenedores de SummanPOS en Docker local.

Modos:
  snapshot  -> guarda docker stats, docker top (procesos/hilos), uso de disco del volumen
               de uploads y del contenedor en un .txt.
  muestreo  -> toma docker stats cada --intervalo segundos durante --segundos y guarda un CSV
               (tiempo, contenedor, cpu_pct, mem_mb, mem_pct, pids).

Uso:
    python agents_scripts/medir_recursos_docker.py snapshot --salida .tmp/manual_tecnico/snapshot_reposo.txt
    python agents_scripts/medir_recursos_docker.py muestreo --segundos 60 --salida .tmp/manual_tecnico/muestreo.csv
Contenedores por defecto: manual_app (Flask/Gunicorn) y manual_pg (PostgreSQL).
"""
import argparse
import csv
import os
import re
import subprocess
import time

DOCKER_BIN = r"C:\Program Files\Docker\Docker\resources\bin"
os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + DOCKER_BIN
PG_USER = os.environ.get("PGUSER") or "postgres"


def sh(cmd: list) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or r.stderr).strip()


def a_mb(txt: str) -> float:
    m = re.match(r"([\d.]+)\s*([KMG]i?B|B)", txt.strip())
    if not m:
        return 0.0
    v, u = float(m.group(1)), m.group(2)
    return v / 1024 if u.startswith("K") else v * 1024 if u.startswith("G") else v / 1048576 if u == "B" else v


def snapshot(app: str, pg: str, salida: str):
    bloques = [
        ("docker stats --no-stream", ["docker", "stats", "--no-stream", "--format",
         "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}", app, pg]),
        (f"docker top {app} (procesos Gunicorn)", ["docker", "top", app, "-o", "pid,ppid,nlwp,pcpu,pmem,rss,etime,args"]),
        (f"docker top {pg} (procesos PostgreSQL)", ["docker", "top", pg, "-o", "pid,pcpu,pmem,rss,args"]),
        ("Disco: archivos en static/uploads", ["docker", "exec", app, "sh", "-c",
         "du -sh /app/static/uploads; ls -la /app/static/uploads | tail -n +2 | head -15"]),
        ("Disco: base de datos", ["docker", "exec", pg, "psql", "-U", PG_USER, "-d",
         "flask_inventario_db", "-c", "SELECT pg_size_pretty(pg_database_size(current_database())) AS tamano_bd;"]),
        ("Disco: imagen, contenedores y volúmenes", ["docker", "system", "df"]),
        ("Límites del contenedor", ["docker", "inspect", app, "--format",
         "CPUs={{.HostConfig.NanoCpus}} Memoria={{.HostConfig.Memory}} Restart={{.HostConfig.RestartPolicy.Name}}"]),
    ]
    partes = []
    for titulo, cmd in bloques:
        partes.append(f"### {titulo}\n$ {' '.join(c if ' ' not in c else repr(c) for c in cmd)}\n{sh(cmd)}\n")
    with open(salida, "w", encoding="utf-8") as f:
        f.write("\n".join(partes))
    print("OK ->", salida)


def muestreo(app: str, pg: str, segundos: int, intervalo: float, salida: str):
    t0 = time.time()
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t", "contenedor", "cpu_pct", "mem_mb", "mem_pct", "pids"])
        while time.time() - t0 < segundos:
            out = sh(["docker", "stats", "--no-stream", "--format",
                      "{{.Name}};{{.CPUPerc}};{{.MemUsage}};{{.MemPerc}};{{.PIDs}}", app, pg])
            t = round(time.time() - t0, 1)
            for linea in out.splitlines():
                p = linea.split(";")
                if len(p) == 5:
                    w.writerow([t, p[0], p[1].rstrip("%"), round(a_mb(p[2].split("/")[0]), 1), p[3].rstrip("%"), p[4]])
            f.flush()
            time.sleep(intervalo)
    print("OK ->", salida)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["snapshot", "muestreo"])
    ap.add_argument("--salida", required=True)
    ap.add_argument("--app", default="manual_app")
    ap.add_argument("--pg", default="manual_pg")
    ap.add_argument("--segundos", type=int, default=60)
    ap.add_argument("--intervalo", type=float, default=1.0)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
    if a.modo == "snapshot":
        snapshot(a.app, a.pg, a.salida)
    else:
        muestreo(a.app, a.pg, a.segundos, a.intervalo, a.salida)


if __name__ == "__main__":
    main()
