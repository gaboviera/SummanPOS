from models import Categorias
from extensions import db
from datetime import datetime

def obtener_categorias_paginadas(page=1, query_str='', per_page=15):
    query = Categorias.query.filter_by(deleted_at=None)
    
    if query_str:
        query = query.filter(Categorias.nombre.ilike(f'%{query_str}%'))
        
    return query.order_by(Categorias.nombre).paginate(page=page, per_page=per_page, error_out=False)

def crear_categoria(nombre):
    if not nombre:
        raise ValueError("El nombre de la categoría es obligatorio.")
        
    existente = Categorias.query.filter_by(nombre=nombre).first()
    if existente:
        if existente.deleted_at:
            existente.deleted_at = None
            db.session.commit()
            return True, "Categoría restaurada con éxito."
        else:
            return False, "La categoría ya existe."
            
    nueva = Categorias(nombre=nombre)
    db.session.add(nueva)
    db.session.commit()
    return True, "Categoría creada exitosamente."

def editar_categoria(id, nombre):
    categoria = Categorias.query.get_or_404(id)
    
    if not nombre:
        raise ValueError("El nombre es obligatorio.")
        
    if nombre != categoria.nombre:
        existente = Categorias.query.filter_by(nombre=nombre).first()
        if existente and existente.id != categoria.id:
            return False, "Ya existe otra categoría con ese nombre."
            
        categoria.nombre = nombre
        db.session.commit()
        return True, "Categoría actualizada con éxito."
        
    return True, "Sin cambios realizados."

def eliminar_categoria(id):
    categoria = Categorias.query.get_or_404(id)
    categoria.deleted_at = datetime.now()
    db.session.commit()
    return True, "Categoría eliminada con éxito."
