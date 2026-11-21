import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(os.getenv('VPS_HOST'), username=os.getenv('VPS_USER'), password=os.getenv('VPS_PASSWORD'))
sftp = ssh.open_sftp()
sftp.put('templates/transacciones.html', '/opt/deploy/transacciones.html')
ssh.exec_command('docker cp /opt/deploy/transacciones.html inventario_app:/app/templates/transacciones.html')
ssh.exec_command('docker exec inventario_app kill -HUP 1')
print('Patched successfully!')
