import urllib.request
import ssl
from bs4 import BeautifulSoup
from datetime import datetime
from models import TasaCambio
from extensions import db

def actualizar_tasa_bcv(app=None):
    """
    Función que raspa la página oficial del BCV y actualiza la tasa en la base de datos.
    Soporta contexto de app para el Cron Job automático.
    """
    def _ejecutar():
        # Ignorar certificados SSL para evitar errores
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        try:
            req = urllib.request.Request('https://www.bcv.org.ve/', headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=20) as response:
                html = response.read().decode('utf-8')
                
                # Usamos BeautifulSoup (mucho más estable que Regex)
                soup = BeautifulSoup(html, 'html.parser')
                dolar_div = soup.find('div', id='dolar')
                
                if dolar_div and dolar_div.find('strong'):
                    tasa_str = dolar_div.find('strong').text.replace(',', '.').strip()
                    tasa_float = float(tasa_str)
                    
                    hoy = datetime.now().date()
                    # Buscamos si ya guardamos una tasa hoy
                    tasa_db = TasaCambio.query.filter_by(fecha=hoy).first()
                    
                    if tasa_db:
                        tasa_db.tasa = tasa_float # Actualizamos si varió
                    else:
                        nueva_tasa = TasaCambio(fecha=hoy, tasa=tasa_float, fuente='BCV')
                        db.session.add(nueva_tasa)
                        
                    db.session.commit()
                    return True, f"Tasa BCV actualizada a {tasa_float} Bs."
                else:
                    return False, "Estructura del BCV cambió, no se encontró el valor."
        except Exception as e:
            db.session.rollback()
            return False, f"Error conectando al BCV: {str(e)}"

    # Si venimos del Cron automático, necesitamos activar el contexto de Flask
    if app:
        with app.app_context():
            return _ejecutar()
    else:
        # Si venimos de la vista web, el contexto ya está activo
        return _ejecutar()
