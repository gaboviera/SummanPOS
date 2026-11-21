from models import Atributos
from extensions import db

def obtener_todos_atributos():
    """Retorna todos los atributos ordenados por nombre"""
    return Atributos.query.filter_by(deleted_at=None).order_by(Atributos.nombre).all()

def guardar_atributo(atributo_id, nombre):
    """Crea o actualiza un atributo en la base de datos"""
    if not nombre:
        raise ValueError("El nombre del atributo es obligatorio.")
    
    # Capitalizar para estandarizar (ej: "color" -> "Color")
    nombre_limpio = nombre.strip().capitalize()

    if atributo_id:
        # EDITAR
        atributo = Atributos.query.get(atributo_id)
        if not atributo:
            raise ValueError("El atributo no existe.")
        
        # Verificar que el nuevo nombre no choque con uno existente (salvo que sea él mismo)
        existe = Atributos.query.filter(Atributos.nombre.ilike(nombre_limpio), Atributos.id != atributo_id).first()
        if existe:
            raise ValueError(f"Ya existe un atributo llamado '{nombre_limpio}'.")
            
        atributo.nombre = nombre_limpio
    else:
        # NUEVO
        existe = Atributos.query.filter(Atributos.nombre.ilike(nombre_limpio)).first()
        if existe:
            raise ValueError(f"Ya existe un atributo llamado '{nombre_limpio}'.")
        
        nuevo_atributo = Atributos(nombre=nombre_limpio)
        db.session.add(nuevo_atributo)
    
    db.session.commit()

def eliminar_atributo(atributo_id):
    """Elimina un atributo por ID (Borrado Lógico)"""
    atributo = Atributos.query.filter_by(id=atributo_id, deleted_at=None).first()
    if not atributo:
        raise ValueError("El atributo no existe.")
    
    from datetime import datetime
    atributo.deleted_at = datetime.now()
    db.session.commit()

# ==========================================
# LÓGICA DE VALORES POR ATRIBUTO
# ==========================================
from models import ValoresAtributos

def obtener_valores_por_atributo(atributo_id):
    """Devuelve la lista de diccionarios de valores para un atributo dado"""
    valores = ValoresAtributos.query.filter_by(atributo_id=atributo_id, deleted_at=None).order_by(ValoresAtributos.valor).all()
    return [{"id": v.id, "valor": v.valor} for v in valores]

def guardar_valor_atributo(atributo_id, valor_texto):
    """Crea un nuevo valor para un atributo, retornando el diccionario creado"""
    if not valor_texto:
        raise ValueError("El valor no puede estar vacío.")
    
    valor_limpio = str(valor_texto).strip().upper()
    
    # Verificar si ya existe para ese atributo
    existe = ValoresAtributos.query.filter(
        ValoresAtributos.atributo_id == atributo_id,
        ValoresAtributos.valor.ilike(valor_limpio)
    ).first()
    
    if existe:
        raise ValueError(f"El valor '{valor_limpio}' ya existe en este atributo.")
        
    nuevo_valor = ValoresAtributos(atributo_id=atributo_id, valor=valor_limpio)
    db.session.add(nuevo_valor)
    db.session.commit()
    
    return {"id": nuevo_valor.id, "valor": nuevo_valor.valor}

def eliminar_valor_atributo(valor_id):
    """Elimina un valor específico (Borrado Lógico)"""
    valor = ValoresAtributos.query.filter_by(id=valor_id, deleted_at=None).first()
    if not valor:
        raise ValueError("El valor no existe.")
    
    from datetime import datetime
    valor.deleted_at = datetime.now()
    db.session.commit()
