import re
from models import Usuario, Rol
from extensions import db, bcrypt

def obtener_todos_usuarios():
    """Retorna todos los usuarios con sus roles asociados."""
    return Usuario.query.join(Rol).order_by(Usuario.id).all()

def obtener_todos_roles():
    """Retorna todos los roles disponibles."""
    return Rol.query.order_by(Rol.id).all()

def validar_datos_usuario(usuario_id, username, password, rol_id):
    """Valida que el nombre de usuario o correo y la contraseña cumplan las reglas del sistema."""
    if not username or not username.strip():
        raise ValueError("El nombre de usuario o correo electrónico es obligatorio.")

    username = username.strip().lower()

    if len(username) < 3 or len(username) > 50:
        raise ValueError("El usuario o correo debe tener entre 3 y 50 caracteres.")

    if " " in username:
        raise ValueError("El nombre de usuario no puede contener espacios en blanco.")

    pattern = r'^(?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|[a-zA-Z0-9][a-zA-Z0-9._-]{1,48}[a-zA-Z0-9]|[a-zA-Z0-9]{3,50})$'
    if not re.match(pattern, username):
        if "@" in username:
            raise ValueError("El correo electrónico no tiene un formato válido (ejemplo: usuario@empresa.com).")
        else:
            raise ValueError("El usuario solo puede contener letras, números, puntos (.), guiones (-) o guiones bajos (_), sin espacios ni caracteres especiales.")

    if not rol_id:
        raise ValueError("Debe seleccionar un rol de acceso.")

    if not usuario_id:
        # Modo Creación
        if not password or len(password.strip()) < 6:
            raise ValueError("La contraseña es obligatoria para nuevos usuarios y debe tener al menos 6 caracteres.")
    else:
        # Modo Edición
        if password and len(password.strip()) < 6:
            raise ValueError("La nueva contraseña debe tener al menos 6 caracteres.")

    return username

def guardar_usuario(usuario_id, username, password, rol_id, activo):
    """Crea un nuevo usuario o actualiza uno existente."""
    username = validar_datos_usuario(usuario_id, username, password, rol_id)

    if usuario_id:
        # Modo Edición
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            raise ValueError("El usuario no existe.")

        # Verificar que el nuevo username no choque con uno existente
        existe = Usuario.query.filter(Usuario.username == username, Usuario.id != usuario_id).first()
        if existe:
            raise ValueError(f"El usuario o correo '{username}' ya está en uso.")

        usuario.username = username
        usuario.rol_id = int(rol_id)
        usuario.activo = True if activo else False

        # Solo actualizamos la contraseña si envió una nueva
        if password and password.strip():
            usuario.password_hash = bcrypt.generate_password_hash(password.strip()).decode('utf-8')

    else:
        # Modo Creación
        existe = Usuario.query.filter_by(username=username).first()
        if existe:
            raise ValueError(f"El usuario o correo '{username}' ya está en uso.")

        nuevo_usuario = Usuario(
            username=username,
            password_hash=bcrypt.generate_password_hash(password.strip()).decode('utf-8'),
            rol_id=int(rol_id),
            activo=True if activo else False
        )
        db.session.add(nuevo_usuario)

    db.session.commit()

def eliminar_usuario(usuario_id):
    """Elimina un usuario por ID. Previene borrar al último administrador."""
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        raise ValueError("El usuario no existe.")

    # Validar que no se borre el último admin
    if usuario.rol.nombre == "Administrador":
        total_admins = Usuario.query.join(Rol).filter(Rol.nombre == "Administrador").count()
        if total_admins <= 1:
            raise ValueError("No puedes eliminar al último Administrador del sistema.")

    db.session.delete(usuario)
    db.session.commit()
