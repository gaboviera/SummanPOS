import paramiko, os
from dotenv import load_dotenv

load_dotenv()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(os.getenv('VPS_HOST'), username=os.getenv('VPS_USER'), password=os.getenv('VPS_PASSWORD'))

def run(cmd):
    print(f'\n> {cmd}')
    _, out, err = ssh.exec_command(cmd)
    out.channel.recv_exit_status()
    o = out.read().decode().strip()
    e = err.read().decode().strip()
    if o:
        print(o)
    if e:
        for line in e.splitlines():
            if 'INFO' not in line:
                print(f'[ERR] {line}')

run('cd /opt/deploy && docker-compose up -d inventario_app')
run('docker ps --format "{{.Names}} | {{.Image}} | {{.Status}}"')

ssh.close()
print('\nListo.')
