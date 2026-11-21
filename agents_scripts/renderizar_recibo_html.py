"""
Diagnostico: renderiza el HTML REAL del recibo (misma plantilla Jinja,
mismo recibo.css, mismos datos de la venta) usando el test_client de Flask
con una sesion de prueba de Flask-Login (session['_user_id']), la tecnica
estandar para probar rutas autenticadas sin usar ninguna contrasena real.

No toca la sesion del navegador del usuario ni ninguna credencial: solo
firma una cookie de sesion de PRUEBA dentro del propio proceso Flask, igual
que cualquier suite de tests.

Uso:
    python agents_scripts/renderizar_recibo_html.py <referencia> <formato> <salida.html>
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'flask_iventario'))

from app import create_app
from models import Usuario

referencia = sys.argv[1]
formato = sys.argv[2]
salida = sys.argv[3]

app = create_app()

with app.app_context():
    usuario = Usuario.query.filter_by(username='admin').first()
    if not usuario:
        print("No existe el usuario 'admin' en esta BD local.")
        sys.exit(1)

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(usuario.id)
        sess['_fresh'] = True

    resp = client.get('/ventas/recibo/%s?formato=%s' % (referencia, formato))
    print("status:", resp.status_code)
    if resp.status_code != 200:
        print(resp.data[:2000])
        sys.exit(1)

    with open(salida, 'wb') as f:
        f.write(resp.data)
    print("guardado:", salida, "(%d bytes)" % len(resp.data))
