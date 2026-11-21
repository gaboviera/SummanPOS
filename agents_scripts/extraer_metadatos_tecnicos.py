"""Extrae metadatos técnicos de flask_iventario/ para el Manual Técnico.

Genera un JSON con:
- tablas: columnas, tipo, PK, FK, NOT NULL, UNIQUE, default (desde los modelos SQLAlchemy).
- rutas: blueprint, prefijo, ruta, métodos HTTP, función, roles requeridos, parámetros
  de formulario/query leídos (análisis estático con ast, sin levantar la app).

Uso:
    python agents_scripts/extraer_metadatos_tecnicos.py --salida .tmp/manual_tecnico/metadatos.json
Requiere Flask, Flask-SQLAlchemy, Flask-Login, Flask-Bcrypt, Flask-Migrate instalados.
"""
import argparse
import ast
import json
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "flask_iventario"))


def extraer_tablas() -> list:
    sys.path.insert(0, RAIZ)
    import models  # noqa: F401
    from extensions import db

    tablas = []
    for t in db.metadata.sorted_tables:
        cols = []
        for c in t.columns:
            restr = []
            if c.primary_key:
                restr.append("PK")
            for fk in c.foreign_keys:
                restr.append(f"FK → {fk.target_fullname}")
            if not c.nullable and not c.primary_key:
                restr.append("NOT NULL")
            if c.unique:
                restr.append("UNIQUE")
            default = None
            if c.default is not None:
                arg = c.default.arg
                default = getattr(arg, "__name__", None) or repr(arg)
            cols.append({
                "nombre": c.name,
                "tipo": str(c.type),
                "restricciones": restr,
                "default": default,
            })
        uniques = [
            [col.name for col in con.columns]
            for con in t.constraints
            if con.__class__.__name__ == "UniqueConstraint" and len(con.columns) > 1
        ]
        tablas.append({"tabla": t.name, "columnas": cols, "unique_compuestos": uniques})
    return tablas


def _str(nodo):
    return nodo.value if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) else None


def extraer_rutas() -> list:
    rutas = []
    carpeta = os.path.join(RAIZ, "routes")
    for archivo in sorted(os.listdir(carpeta)):
        if not archivo.endswith("_routes.py"):
            continue
        arbol = ast.parse(open(os.path.join(carpeta, archivo), encoding="utf-8").read())
        prefijos = {}
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.Call) \
                    and getattr(nodo.value.func, "id", "") == "Blueprint":
                nombre_var = nodo.targets[0].id
                bp_name = _str(nodo.value.args[0])
                pref = next((_str(k.value) for k in nodo.value.keywords if k.arg == "url_prefix"), "")
                prefijos[nombre_var] = (bp_name, pref or "")
        protegidos = set()
        for nodo in arbol.body:
            if isinstance(nodo, ast.FunctionDef):
                for dec in nodo.decorator_list:
                    if isinstance(dec, ast.Attribute) and dec.attr == "before_request":
                        src = ast.unparse(nodo)
                        if "is_authenticated" in src or "login_required" in src:
                            protegidos.add(dec.value.id)
        for nodo in arbol.body:
            if not isinstance(nodo, ast.FunctionDef):
                continue
            roles, login = [], False
            defs = []
            for dec in nodo.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "route":
                    var = dec.func.value.id
                    path = _str(dec.args[0])
                    metodos = ["GET"]
                    for k in dec.keywords:
                        if k.arg == "methods":
                            metodos = [_str(e) for e in k.value.elts]
                    defs.append((var, path, metodos))
                elif isinstance(dec, ast.Call) and getattr(dec.func, "id", "") == "rol_requerido":
                    roles = [_str(a) for a in dec.args]
                elif getattr(dec, "id", "") == "login_required":
                    login = True
            if not defs:
                continue
            params = set()
            for sub in ast.walk(nodo):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
                        and sub.func.attr in ("get", "getlist") \
                        and isinstance(sub.func.value, ast.Attribute) \
                        and sub.func.value.attr in ("form", "args", "files") and sub.args:
                    v = _str(sub.args[0])
                    if v:
                        params.add(f"{sub.func.value.attr}:{v}")
                if isinstance(sub, ast.Attribute) and sub.attr in ("get_json", "json"):
                    params.add("json:body")
            responde_json = any(
                isinstance(s, ast.Call) and getattr(s.func, "id", "") == "jsonify" for s in ast.walk(nodo)
            )
            doc = (ast.get_docstring(nodo) or "").strip().split("\n")[0]
            for var, path, metodos in defs:
                bp_name, pref = prefijos.get(var, (var, ""))
                rutas.append({
                    "archivo": archivo,
                    "blueprint": bp_name,
                    "ruta": (pref.rstrip("/") + path) if pref else path,
                    "metodos": metodos,
                    "funcion": nodo.name,
                    "roles": roles or (["Autenticado"] if (login or var in protegidos) else ["Público"]),
                    "parametros": sorted(params),
                    "respuesta": "JSON" if responde_json else "HTML/Redirect",
                    "doc": doc,
                })
    return rutas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", required=True)
    a = ap.parse_args()
    datos = {"tablas": extraer_tablas(), "rutas": extraer_rutas()}
    os.makedirs(os.path.dirname(a.salida), exist_ok=True)
    with open(a.salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    print(f"tablas={len(datos['tablas'])} rutas={len(datos['rutas'])} -> {a.salida}")


if __name__ == "__main__":
    main()
