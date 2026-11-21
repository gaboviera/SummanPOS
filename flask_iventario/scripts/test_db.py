import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(os.getenv('VPS_HOST'), username=os.getenv('VPS_USER'), password = os.getenv('VPS_PASSWORD'))
cmd = "docker exec inventario_app python -c \\"from app import app, db; from sqlalchemy import inspect; print('COLUMNS:', [c['name'] for c in inspect(db.engine).get_columns('detalle_orden_compra')])\\""
_, out, err = ssh.exec_command(cmd)
print('OUT:', out.read().decode())
print('ERR:', err.read().decode())
