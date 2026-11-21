import os
import paramiko
vps_host = os.environ.get('VPS_HOST')
vps_user = os.environ.get('VPS_USER', 'root')
vps_password = os.environ.get('VPS_PASSWORD')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(vps_host, username=vps_user, password=vps_password, timeout=15)
stdin, stdout, stderr = ssh.exec_command('docker ps --format "{{.Names}}"')
print("CONTAINERS:", stdout.read().decode('utf-8'))
ssh.close()
