import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

def run_remote_patch():
    host     = os.getenv('VPS_HOST')
    user     = os.getenv('VPS_USER')
    password = os.getenv('VPS_PASSWORD')
    
    print("Conectando al servidor...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    sftp = ssh.open_sftp()
    
    print("Subiendo archivos modificados a /tmp...")
    sftp.put('models.py', '/tmp/models.py')
    sftp.put('services/bcv_service.py', '/tmp/bcv_service.py')
    sftp.put('services/binance_service.py', '/tmp/binance_service.py')
    sftp.close()
    
    commands = [
        "docker cp /tmp/models.py inventario_app:/app/models.py",
        "docker cp /tmp/bcv_service.py inventario_app:/app/services/bcv_service.py",
        "docker cp /tmp/binance_service.py inventario_app:/app/services/binance_service.py",
        "docker exec inventario_app flask db migrate -m 'change_fecha_to_datetime'",
        "docker exec inventario_app flask db upgrade",
        "docker restart inventario_app"
    ]
    
    for cmd in commands:
        print(f"Ejecutando: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        # Esperar a que termine el comando
        exit_status = stdout.channel.recv_exit_status()
        
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        
        if out:
            print(f"Salida: {out}")
        if err:
            print(f"Error: {err}")
            
    ssh.close()
    print("Proceso completado exitosamente.")

if __name__ == '__main__':
    run_remote_patch()
