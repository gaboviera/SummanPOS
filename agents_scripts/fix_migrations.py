import os
import paramiko
vps_host = os.environ.get('VPS_HOST')
vps_user = os.environ.get('VPS_USER', 'root')
vps_password = os.environ.get('VPS_PASSWORD')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(vps_host, username=vps_user, password=vps_password, timeout=15)
stdin, stdout, stderr = ssh.exec_command('docker exec dev-summanpos_inventario_app_1 flask db migrate -m "add_ciudad_to_guias_and_contactos"')
print("STDOUT MIGRATE:", stdout.read().decode('utf-8'))
print("STDERR MIGRATE:", stderr.read().decode('utf-8'))

stdin, stdout, stderr = ssh.exec_command('docker exec dev-summanpos_inventario_app_1 flask db upgrade')
print("STDOUT UPGRADE:", stdout.read().decode('utf-8'))
print("STDERR UPGRADE:", stderr.read().decode('utf-8'))

ssh.close()
