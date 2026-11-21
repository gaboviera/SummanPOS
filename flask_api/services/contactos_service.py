from models import Contactos
from extensions import db
import time

def obtener_todos_contactos(tipo=None):
    """Retorna todos los contactos ordenados por nombre, opcionalmente filtrados por tipo"""
    query = Contactos.query.filter_by(deleted_at=None)
    if tipo:
        tipo_lower = tipo.lower()
        if tipo_lower in ['cliente', 'clientes']:
            query = query.filter(Contactos.tipo.in_(['Cliente', 'Ambos']))
        elif tipo_lower in ['proveedor', 'proveedores']:
            query = query.filter(Contactos.tipo.in_(['Proveedor', 'Ambos']))
        elif tipo_lower in ['usuario', 'usuarios', 'contacto usuario']:
            query = query.filter(Contactos.tipo.in_(['Contacto Usuario', 'Usuario']))
        elif tipo_lower in ['sin_definir', 'sin definir']:
            query = query.filter(Contactos.tipo.in_(['Sin Definir', None]))
        elif tipo_lower == 'ambos':
            query = query.filter(Contactos.tipo == 'Ambos')
        else:
            query = query.filter(Contactos.tipo == tipo)
    return query.order_by(Contactos.nombre).all()

def obtener_lista_diccionarios_contactos(tipo=None, solo_clientes=False):
    """Retorna los contactos como lista de diccionarios para JSON"""
    filtro_tipo = 'cliente' if solo_clientes else tipo
    contactos = obtener_todos_contactos(tipo=filtro_tipo)
    return [{
        "id": c.id,
        "identificacion": c.identificacion,
        "nombre": c.nombre,
        "correo": c.correo,
        "direccion": c.direccion,
        "telefono": c.telefono,
        "tipo": c.tipo or 'Cliente'
    } for c in contactos]

def guardar_contacto(contacto_id, identificacion, nombre, correo, direccion, telefono, tipo='Cliente'):
    """Crea o actualiza un contacto en la base de datos"""
    if not nombre or not identificacion:
        raise ValueError("El nombre y RIF/CI son obligatorios.")

    tipos_validos = ['Cliente', 'Proveedor', 'Ambos', 'Contacto Usuario', 'Usuario', 'Sin Definir']
    tipo_valido = tipo if tipo in tipos_validos else 'Cliente'

    if contacto_id:
        # EDITAR
        contacto = Contactos.query.get(contacto_id)
        if not contacto:
            raise ValueError("El contacto no existe.")
        contacto.identificacion = identificacion
        contacto.nombre = nombre
        contacto.correo = correo
        contacto.direccion = direccion
        contacto.telefono = telefono
        contacto.tipo = tipo_valido
    else:
        # NUEVO
        # Verificar si ya existe RIF
        existe = Contactos.query.filter_by(identificacion=identificacion).first()
        if existe:
            raise ValueError(f"Ya existe un contacto con el RIF/CI: {identificacion}")
            
        nuevo = Contactos(
            identificacion=identificacion,
            nombre=nombre,
            correo=correo,
            direccion=direccion,
            telefono=telefono,
            tipo=tipo_valido
        )
        db.session.add(nuevo)
    
    db.session.commit()

def eliminar_contacto(contacto_id):
    """Elimina un contacto por su ID (Borrado Lógico)"""
    contacto = Contactos.query.filter_by(id=contacto_id, deleted_at=None).first()
    if not contacto:
        raise ValueError("El contacto no existe.")
        
    from datetime import datetime
    contacto.deleted_at = datetime.now()
    db.session.commit()

def asegurar_contacto_existente(cliente_data):
    """Verifica si un contacto existe por RIF o Nombre. Si no, lo crea. Retorna el contacto."""
    identificacion = cliente_data.get('identificacion')
    nombre = cliente_data.get('nombre')

    if not identificacion and not nombre:
        return None

    contacto = None
    if identificacion:
        contacto = Contactos.query.filter_by(identificacion=identificacion).first()
    
    if not contacto and nombre:
        contacto = Contactos.query.filter_by(nombre=nombre).first()
    
    if not contacto:
        # Crear nuevo si no existe como Cliente
        contacto = Contactos(
            identificacion=identificacion or f"GEN-{int(time.time())}",
            nombre=nombre,
            direccion=cliente_data.get('direccion'),
            telefono=cliente_data.get('telefono'),
            tipo='Cliente'
        )
        db.session.add(contacto)
        # No hacemos commit aquí, el commit se hará junto con la transacción de venta
    
    return contacto
