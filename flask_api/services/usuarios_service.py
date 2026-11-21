from models import Usuario, Rol
from extensions import db, bcrypt

def obtener_todos_usuarios():
    """Retorna todos los usuarios con sus roles asociados."""
    return Usuario.query.join(Rol).order_by(Usuario.id).all()

def obtener_todos_roles():
    """Retorna todos los roles disponibles."""
    return Rol.query.order_by(Rol.id).all()

def guardar_usuario(usuario_id, username, password, rol_id, activo):
    """Crea un nuevo usuario o actualiza uno existente."""
    if not username or not rol_id:
        raise ValueError("El nombre de usuario y el rol son obligatorios.")
    
    username = username.strip().lower()

    if usuario_id:
        # Modo Edición
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            raise ValueError("El usuario no existe.")
            
        # Verificar que el nuevo username no choque con uno existente
        existe = Usuario.query.filter(Usuario.username == username, Usuario.id != usuario_id).first()
        if existe:
            raise ValueError(f"El usuario '{username}' ya está en uso.")
            
        usuario.username = username
        usuario.rol_id = int(rol_id)
        usuario.activo = True if activo else False
        
        # Solo actualizamos la contraseña si envió una nueva
        if password and password.strip():
            usuario.password_hash = bcrypt.generate_password_hash(password.strip()).decode('utf-8')
            
    else:
        # Modo Creación
        if not password:
            raise ValueError("La contraseña es obligatoria para usuarios nuevos.")
            
        existe = Usuario.query.filter_by(username=username).first()
        if existe:
            raise ValueError(f"El usuario '{username}' ya está en uso.")
            
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
