import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

def check_db():
    host = os.getenv('VPS_HOST')
    user = os.getenv('VPS_USER')
    password = os.getenv('VPS_PASSWORD')
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=user, password=password)
        
        # Correr comando en docker para consultar la tabla notificaciones
        cmd = '''docker exec inventario_app python -c "from app import create_app; from extensions import db; from models import Notificacion, Productos; app = create_app();
with app.app_context():
    print(f'Total Productos: {Productos.query.count()}')
    notifs = Notificacion.query.all()
    for n in notifs:
        print(f'Notificacion: {n.mensaje} (Tipo: {n.tipo})')
"
'''
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print("Salida:")
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print("Error:")
            print(err)
            
    except Exception as e:
        print(f"SSH Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    check_db()
