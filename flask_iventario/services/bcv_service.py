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
                euro_div = soup.find('div', id='euro')
                
                cambios = False
                mensajes = []

                if dolar_div and dolar_div.find('strong'):
                    tasa_str = dolar_div.find('strong').text.replace(',', '.').strip()
                    tasa_dolar = float(tasa_str)
                    ultima_tasa = TasaCambio.query.filter_by(fuente='BCV').order_by(TasaCambio.id.desc()).first()
                    
                    if not ultima_tasa or float(ultima_tasa.tasa) != tasa_dolar:
                        db.session.add(TasaCambio(fecha=datetime.now(), tasa=tasa_dolar, fuente='BCV'))
                        cambios = True
                    mensajes.append(f"Dólar BCV: {tasa_dolar:,.2f} Bs.")

                # Actualizar Euro BCV automáticamente si hay cambio o si no existe
                if euro_div and euro_div.find('strong'):
                    tasa_str = euro_div.find('strong').text.replace(',', '.').strip()
                    tasa_euro = float(tasa_str)
                    ultima_tasa_euro = TasaCambio.query.filter_by(fuente='BCV_EURO').order_by(TasaCambio.id.desc()).first()
                    
                    if not ultima_tasa_euro or float(ultima_tasa_euro.tasa) != tasa_euro:
                        db.session.add(TasaCambio(fecha=datetime.now(), tasa=tasa_euro, fuente='BCV_EURO'))
                        cambios = True
                    mensajes.append(f"Euro BCV: {tasa_euro:,.2f} Bs.")

                if mensajes:
                    db.session.commit()
                    return True, " | ".join(mensajes)
                else:
                    return False, "No se encontraron las estructuras de tasas en la web del BCV."
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


def actualizar_tasa_euro_bcv():
    """Actualiza explícitamente la tasa Euro desde la web oficial del BCV."""
    from app import db
    from models import TasaCambio
    from datetime import datetime
    import urllib.request, ssl
    from bs4 import BeautifulSoup
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(
        'https://www.bcv.org.ve/',
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as res:
            soup = BeautifulSoup(res.read().decode('utf-8'), 'html.parser')
            euro_div = soup.find('div', id='euro')
            if euro_div and euro_div.find('strong'):
                tasa_str = euro_div.find('strong').text.replace(',', '.').strip()
                tasa_euro = float(tasa_str)
                db.session.add(TasaCambio(fecha=datetime.now(), tasa=tasa_euro, fuente='BCV_EURO'))
                db.session.commit()
                return True, f"Euro BCV actualizado desde la web oficial: {tasa_euro:,.4f} Bs."
            return False, "No se encontró la tasa de Euro en la web del BCV."
    except Exception as e:
        db.session.rollback()
        return False, f"Error conectando al BCV: {str(e)}"
