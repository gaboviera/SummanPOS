import os
import paramiko
vps_host = os.environ.get('VPS_HOST')
vps_user = os.environ.get('VPS_USER', 'root')
vps_password = os.environ.get('VPS_PASSWORD')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(vps_host, username=vps_user, password=vps_password, timeout=15)
sftp = ssh.open_sftp()
stdin, stdout, stderr = ssh.exec_command('docker cp dev-summanpos_inventario_app_1:/app/migrations/versions/e1fec70652d9_add_ciudad_to_guias_and_contactos.py /tmp/migration.py')
stdout.channel.recv_exit_status()
sftp.get('/tmp/migration.py', 'flask_iventario/migrations/versions/e1fec70652d9_add_ciudad_to_guias_and_contactos.py')
ssh.close()
