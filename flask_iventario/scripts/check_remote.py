import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

import sys

def check_server():
    host = os.getenv('VPS_HOST')
    user = os.getenv('VPS_USER')
    password = os.getenv('VPS_PASSWORD')
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=user, password=password)
        
        print("--- APP LOGS ---")
        stdin, stdout, stderr = ssh.exec_command("docker logs --tail 50 inventario_app")
        print(stdout.read().decode())
        print(stderr.read().decode())
        
        print("\n--- CADDY LOGS ---")
        stdin, stdout, stderr = ssh.exec_command("docker logs --tail 50 $(docker ps -q -f name=caddy)")
        print(stdout.read().decode())
        print(stderr.read().decode())
        
        print("\n--- CURL LOCALHOST ---")
        stdin, stdout, stderr = ssh.exec_command("docker exec inventario_app curl -s -I http://localhost:5000")
        print(stdout.read().decode())
        print(stderr.read().decode())

    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    check_server()
