import paramiko
import os
from dotenv import load_dotenv

load_dotenv()


def restart_server():
    host = os.getenv('VPS_HOST')
    user = os.getenv('VPS_USER')
    password = os.getenv('VPS_PASSWORD')
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=user, password=password)
        print("Pulling latest image and restarting...")
        stdin, stdout, stderr = ssh.exec_command("cd /opt/deploy && docker-compose pull inventario_app && docker-compose up -d inventario_app")
        print(stdout.read().decode())
        print(stderr.read().decode())
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    restart_server()
