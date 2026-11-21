import urllib.request
import json
import ssl
from datetime import datetime
from models import TasaCambio
from extensions import db

def actualizar_tasa_usdt(app=None):
    """
    Consume la API pública de Binance para obtener el par USDT/VES.
    Guarda el valor en la tabla TasaCambio con fuente BINANCE_USDT.
    """
    def _ejecutar():
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            # Obtenemos la tasa desde el mercado P2P de Binance (USDT/VES)
            url = 'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search'
            headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
            payload = json.dumps({
                'proMerchantAds': False, 'page': 1, 'rows': 10, 'payTypes': [], 
                'countries': [], 'publisherType': None, 'asset': 'USDT', 'fiat': 'VES', 'tradeType': 'BUY'
            }).encode('utf-8')
            req = urllib.request.Request(url, data=payload, headers=headers)
            
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    items = data.get('data', [])
                    if not items:
                        return False, "No se encontraron ofertas en Binance P2P."
                    
                    precios = [float(x['adv']['price']) for x in items if 'adv' in x and 'price' in x['adv']]
                    if not precios:
                        return False, "No se pudieron extraer los precios de Binance P2P."
                    
                    # Promedio de las 10 mejores ofertas para alinearse al mercado P2P general
                    tasa_float = round(sum(precios) / len(precios), 2)
                    
                    if tasa_float <= 0:
                        return False, "Valor de tasa USDT inválido desde Binance."

                    # Buscar la última tasa USDT guardada
                    ultima_tasa = TasaCambio.query.filter_by(fuente='BINANCE_USDT').order_by(TasaCambio.id.desc()).first()
                    
                    if ultima_tasa:
                        tiempo_transcurrido = datetime.now() - ultima_tasa.fecha
                        if tiempo_transcurrido.total_seconds() < 300:
                            return True, f"La tasa USDT se actualizó recientemente a {ultima_tasa.tasa:,.2f} Bs."
                            
                    if not ultima_tasa or ultima_tasa.tasa != tasa_float:
                        nueva_tasa = TasaCambio(fecha=datetime.now(), tasa=tasa_float, fuente='BINANCE_USDT')
                        db.session.add(nueva_tasa)
                        db.session.commit()
                        return True, f"Nueva tasa USDT guardada a {tasa_float:,.2f} Bs."
                    else:
                        return True, f"La tasa USDT se mantiene en {tasa_float:,.2f} Bs."
                else:
                    return False, f"Error HTTP {response.status} de Binance."
        except Exception as e:
            db.session.rollback()
            return False, f"Error conectando a Binance API: {str(e)}"

    if app:
        with app.app_context():
            return _ejecutar()
    else:
        return _ejecutar()
