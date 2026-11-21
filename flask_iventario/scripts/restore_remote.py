import paramiko
import os
from dotenv import load_dotenv

load_dotenv()


def run_restore():
    host = os.getenv('VPS_HOST')
    user = os.getenv('VPS_USER')
    password = os.getenv('VPS_PASSWORD')
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=user, password=password)
        
        print("Restoring database to Azure (with clean, if-exists, no-owner, no-acl)...")
        # Use --clean --if-exists to replace any tables the app might have auto-created
        # Use --no-owner --no-privileges to avoid role errors from local dump (like 'role postgres does not exist')
        restore_cmd = f"docker run --rm -v /opt/deploy:/opt/deploy postgres:17-alpine sh -c \"PGPASSWORD='{os.getenv('PGPASSWORD')}' pg_restore -h {os.getenv('PGHOST')} -p 5432 -U flask_inventario -d flask_inventario_db --clean --if-exists --no-owner --no-privileges /opt/deploy/flask_inventario.sql\""
        
        stdin, stdout, stderr = ssh.exec_command(restore_cmd)
        print("Restore OUT:", stdout.read().decode())
        print("Restore ERR:", stderr.read().decode())
        
        print("Restarting app...")
        ssh.exec_command("cd /opt/deploy && docker-compose restart inventario_app")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    run_restore()
