import os
import paramiko
vps_host = os.environ.get('VPS_HOST')
vps_user = os.environ.get('VPS_USER', 'root')
vps_password = os.environ.get('VPS_PASSWORD')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(vps_host, username=vps_user, password=vps_password, timeout=15)
stdin, stdout, stderr = ssh.exec_command('docker logs --tail 200 dev-summanpos_inventario_app_1')
print("STDOUT:", stdout.read().decode('utf-8'))
print("STDERR:", stderr.read().decode('utf-8'))
ssh.close()
