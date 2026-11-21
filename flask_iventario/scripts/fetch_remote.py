import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

import sys

def fetch_files():
    host = os.getenv('VPS_HOST')
    user = os.getenv('VPS_USER')
    password = os.getenv('VPS_PASSWORD')
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=user, password=password)
        sftp = ssh.open_sftp()
        
        try:
            sftp.get('/opt/deploy/docker-compose.yml', 'remote_docker-compose.yml')
            print("Successfully fetched docker-compose.yml")
        except Exception as e:
            print(f"Error fetching docker-compose.yml: {e}")
            
        try:
            sftp.get('/opt/deploy/.env', 'remote_env')
            print("Successfully fetched .env")
        except Exception as e:
            print(f"Error fetching .env: {e}")
            
        sftp.close()
    except Exception as e:
        print(f"Connection failed: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    fetch_files()
