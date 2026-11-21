from models import Usuario
from extensions import bcrypt

def verificar_credenciales(username, password_plana):
  """
  Busca al usuario en la base de datos y verifica si la contraseña coincide con el Hash.
  Retorna el objeto Usuario si es exitoso, o None si falla.
  """
  usuario = Usuario.query.filter_by(username=username).first()
  if usuario and bcrypt.check_password_hash(usuario. password_hash, password_plana):
    return usuario
  else:
    return None

def encriptar_password(password_plana):
    """
    Recibe una contraseña plana y devuelve un hash seguro para guardar en PostgreSQL.
    """
    return bcrypt.generate_password_hash(password_plana).decode('utf-8')



