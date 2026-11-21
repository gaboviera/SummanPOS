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
        "ciudad": c.ciudad,
        "telefono": c.telefono,
        "tipo": getattr(c, 'tipo', 'Cliente') or 'Cliente',
        "lista_precio_id": c.lista_precio_id,
        "lista_precio_nombre": c.lista_precio.nombre if c.lista_precio else None,
        "lista_precio_moneda": c.lista_precio.moneda if c.lista_precio else None
    } for c in contactos]

def guardar_contacto(contacto_id, identificacion, nombre, correo, direccion, ciudad, telefono, tipo='Cliente', lista_precio_id=None):
    """Crea o actualiza un contacto en la base de datos"""
    if not nombre or not identificacion:
        raise ValueError("El nombre y RIF/CI son obligatorios.")

    tipo_valido = tipo if tipo in ['Cliente', 'Proveedor', 'Ambos', 'Contacto Usuario', 'Usuario', 'Sin Definir'] else 'Cliente'

    lp_id = None
    if lista_precio_id not in [0, '0', '', 'None', None]:
        try:
            lp_id = int(lista_precio_id)
        except (ValueError, TypeError):
            lp_id = None

    if contacto_id:
        # EDITAR
        contacto = Contactos.query.get(contacto_id)
        if not contacto:
            raise ValueError("El contacto no existe.")
        contacto.identificacion = identificacion
        contacto.nombre = nombre
        contacto.correo = correo
        contacto.direccion = direccion
        contacto.ciudad = ciudad
        contacto.telefono = telefono
        contacto.tipo = tipo_valido
        contacto.lista_precio_id = lp_id
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
            ciudad=ciudad,
            telefono=telefono,
            tipo=tipo_valido,
            lista_precio_id=lp_id
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

    lp_id = None
    raw_lp = cliente_data.get('lista_precio_id')
    if raw_lp not in [None, '', 'base', 0, '0', 'None']:
        try:
            lp_id = int(raw_lp)
        except (ValueError, TypeError):
            lp_id = None

    actualizar_tasa = cliente_data.get('actualizar_tasa', True)

    contacto = None
    if identificacion:
        contacto = Contactos.query.filter_by(identificacion=identificacion).first()
    
    if not contacto and nombre:
        contacto = Contactos.query.filter_by(nombre=nombre).first()
    
    if not contacto:
        # Crear nuevo si no existe como Cliente asignando la tasa con la que se vendió
        contacto = Contactos(
            identificacion=identificacion or f"GEN-{int(time.time())}",
            nombre=nombre,
            direccion=cliente_data.get('direccion'),
            ciudad=cliente_data.get('ciudad'),
            telefono=cliente_data.get('telefono'),
            tipo='Cliente',
            lista_precio_id=lp_id
        )
        db.session.add(contacto)
        # No hacemos commit aquí, el commit se hará junto con la transacción de venta
    else:
        # Si el contacto existe, actualizar sus datos vacíos o su tasa si está habilitado
        if lp_id and (actualizar_tasa or not contacto.lista_precio_id):
            contacto.lista_precio_id = lp_id
        if not contacto.direccion and cliente_data.get('direccion'):
            contacto.direccion = cliente_data.get('direccion')
        if not contacto.ciudad and cliente_data.get('ciudad'):
            contacto.ciudad = cliente_data.get('ciudad')
        if not contacto.telefono and cliente_data.get('telefono'):
            contacto.telefono = cliente_data.get('telefono')
    
    return contacto
