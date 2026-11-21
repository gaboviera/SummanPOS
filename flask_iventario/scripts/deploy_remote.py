import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

import sys
import os

def deploy():
    host = os.getenv('VPS_HOST')
    user = os.getenv('VPS_USER')
    password = os.getenv('VPS_PASSWORD')
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("Connecting to SSH...")
        ssh.connect(host, username=user, password=password)
        sftp = ssh.open_sftp()
        
        # 1. Update .env
        print("Updating .env...")
        env_vars = f"""
# Flask Inventario Config
PGHOST={os.getenv('PGHOST')}
PGPORT=5432
PGDATABASE=flask_inventario_db
PGUSER=flask_inventario
PGPASSWORD='{os.getenv('PGPASSWORD')}'
"""
        with sftp.open('/opt/deploy/.env', 'a') as f:
            f.write(env_vars)
            
        # 2. Update docker-compose.yml
        print("Updating docker-compose.yml...")
        service_yaml = """
  inventario_app:
    image: gabrielviera2000/flask-inventario:latest
    container_name: inventario_app
    restart: always
    environment:
      - FLASK_APP=app.py
      - FLASK_ENV=production
      - DB_USER=${PGUSER}
      - DB_PASSWORD=${PGPASSWORD}
      - DB_HOST=${PGHOST}
      - DB_PORT=${PGPORT}
      - DB_NAME=${PGDATABASE}
      - PGSSLMODE=require
    networks:
      - frontend
"""
        # Read the current docker compose, insert before 'networks:' or just append if networks is already there.
        # It's safer to just inject it before the line 'networks:'
        remote_compose = sftp.file('/opt/deploy/docker-compose.yml', 'r').read().decode('utf-8')
        if 'inventario_app:' not in remote_compose:
            # We insert it before the first unindented 'networks:'
            parts = remote_compose.split('\nnetworks:')
            if len(parts) > 1:
                new_compose = parts[0] + service_yaml + "\nnetworks:" + parts[1]
                with sftp.open('/opt/deploy/docker-compose.yml', 'w') as f:
                    f.write(new_compose)
                    
        # 3. Update Caddyfile
        print("Updating Caddyfile...")
        try:
            remote_caddy = sftp.file('/opt/deploy/Caddyfile', 'r').read().decode('utf-8')
        except:
            remote_caddy = ""
            
        caddy_block = """
mini-erp.summantech.com {
    reverse_proxy inventario_app:5000
}
"""
        if 'mini-erp.summantech.com' not in remote_caddy:
            with sftp.open('/opt/deploy/Caddyfile', 'a') as f:
                f.write(caddy_block)
                
        # 4. Upload SQL dump
        print("Uploading flask_inventario.sql...")
        sftp.put('db_dumps/flask_inventario.sql', '/opt/deploy/flask_inventario.sql')
        
        sftp.close()
        
        # 5. Restore database using temporary container
        print("Restoring database to Azure...")
        # Note: No --clean here just in case the db is empty to avoid erroring out
        restore_cmd = f"docker run --rm -v /opt/deploy:/opt/deploy postgres:17-alpine sh -c \"PGPASSWORD='{os.getenv('PGPASSWORD')}' pg_restore -h {os.getenv('PGHOST')} -p 5432 -U flask_inventario -d flask_inventario_db /opt/deploy/flask_inventario.sql\""
        stdin, stdout, stderr = ssh.exec_command(restore_cmd)
        print("Restore output:", stdout.read().decode())
        print("Restore errors:", stderr.read().decode())
        
        # 6. Deploy via docker-compose
        print("Deploying docker-compose...")
        stdin, stdout, stderr = ssh.exec_command("cd /opt/deploy && docker-compose up -d")
        print("Deploy output:", stdout.read().decode())
        print("Deploy errors:", stderr.read().decode())
        
        # Caddy might need reload if it was already running without changes being detected by compose up
        ssh.exec_command("docker exec $(docker ps -q -f name=caddy) caddy reload -c /etc/caddy/Caddyfile")
        
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == '__main__':
    deploy()
