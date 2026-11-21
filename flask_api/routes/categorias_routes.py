from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import Categorias
from extensions import db
from datetime import datetime
from flask_login import login_required

categorias_bp = Blueprint('categorias', __name__, url_prefix='/categorias')

@categorias_bp.before_request
# @login_required
def requerir_login():
    pass

@categorias_bp.route('/')
def listar():
   # page = request.args.get('page', 1, type=int)
    query_str = request.args.get('q', '').strip()

    query = Categorias.query.filter_by(deleted_at=None)

    if query_str:
        query = query.filter(Categorias.nombre.ilike(f'%{query_str}%'))

    # categorias = query.order_by(Categorias.nombre).paginate(page=page, per_page=15, error_out=False)

    # Ejecutamos la consulta (por ahora traemos todas sin paginar para simplificar la API inicial)
    categorias = query.order_by(Categorias.nombre).all()
    
  # return render_template('categorias.html', categorias=categorias, query_str=query_str)

   # Convertimos los objetos de la BD a una lista de diccionarios
    resultado = []
    for cat in categorias:
        resultado.append({
            "id": cat.id,
            "nombre": cat.nombre,
            "delete_at": cat.deleted_at
            
        })
    # Devolvemos el JSON
    return jsonify(resultado)


@categorias_bp.route('/crear', methods=['POST'])
def crear():

    # 1. En lugar de request.form, leemos el JSON que nos envía el cliente (Postman o React Native)
    data = request.get_json()

    # nombre = request.form.get('nombre')

    # 2. Extraemos el nombre. Usamos un diccionario vacío {} por si "data" es None
    nombre = data.get('nombre') if data else None

    # if not nombre:
    #    flash("El nombre de la categoría es obligatorio.", "danger")
    #    return redirect(url_for('categorias.listar'))
    
    # Validamos que el nombre exista
    if not nombre:
        return jsonify({"success": False, "message": "El nombre de la categoría es obligatorio."}), 400
    
    #existente = Categorias.query.filter_by(nombre=nombre).first()
    #if existente:
     #   if existente.deleted_at:
      #      # Restaurar si estaba eliminada
       #     existente.deleted_at = None
        #    db.session.commit()
         #   flash("Categoría restaurada con éxito.", "success")
        #else:
         #   flash("La categoría ya existe.", "warning")
        #return redirect(url_for('categorias.listar'))

    #nueva = Categorias(nombre=nombre)
    #db.session.add(nueva)
    #db.session.commit()
    #flash("Categoría creada exitosamente.", "success")|
    #return redirect(url_for('categorias.listar'))

    existente = Categorias.query.filter_by(nombre=nombre).first()
    if existente:
        if existente.deleted_at:
            # Restaurar si estaba eliminada
            existente.deleted_at = None
            db.session.commit()
            return jsonify({"success": True, "message": "Categoría restaurada con éxito.", "id": existente.id}), 200
        else:
            return jsonify({"success": False, "message": "La categoría ya existe."}), 409

    # 3. Si todo está bien, creamos la categoría
    nueva = Categorias(nombre=nombre)
    db.session.add(nueva)
    db.session.commit()
    
    # 4. Devolvemos una respuesta exitosa y el ID recién creado
    return jsonify({"success": True, "message": "Categoría creada exitosamente.", "id": nueva.id}), 201
        

@categorias_bp.route('/editar/<int:id>', methods=['PUT'])
def editar(id):
    categoria = Categorias.query.get_or_404(id)
    data = request.get_json()
    # nombre = request.form.get('nombre')
    nombre = data.get('nombre') if data else None

    if not nombre:
     return jsonify({"success": False, "message": "El nuevo nombre es obligatorio."}), 400
    
    #if nombre and nombre != categoria.nombre:
    #   existente = Categorias.query.filter_by(nombre=nombre).first()
    #   if existente and existente.id != categoria.id:
    #      flash("Ya existe otra categoría con ese nombre.", "danger")
    #      return redirect(url_for('categorias.listar'))
            
    #   categoria.nombre = nombre
    #    db.session.commit()
    #    flash("Categoría actualizada con éxito.", "success")
    #return redirect(url_for('categorias.listar'))

    if nombre != categoria.nombre:
        existente = Categorias.query.filter_by(nombre=nombre).first()
        if existente and existente.id != categoria.id:
            return jsonify({"success": False, "message": "Ya existe otra categoría con ese nombre."}), 409
            
        categoria.nombre = nombre
        db.session.commit()
        return jsonify({"success": True, "message": "Categoría actualizada con éxito.", "categoria": {"id": categoria.id, "nombre": categoria.nombre}}), 200
        
    # Si el nombre enviado es igual al que ya tenía, respondemos que todo está OK sin hacer nada
    return jsonify({"success": True, "message": "Sin cambios."}), 200

    
#@categorias_bp.route('/eliminar/<int:id>', methods=['DELETE'])
#def eliminar(id):
#    categoria = Categorias.query.get_or_404(id)
#    # Soft delete
#    categoria.deleted_at = datetime.now()
#    db.session.commit()
#    flash("Categoría eliminada con éxito.", "success")
#    return redirect(url_for('categorias.listar'))

@categorias_bp.route('/eliminar/<int:id>', methods=['DELETE'])
def eliminar(id):
    categoria = Categorias.query.get_or_404(id)
    # Soft delete: En lugar de borrarla de la BD, le ponemos fecha de eliminación
    categoria.deleted_at = datetime.now()
    db.session.commit()
    return jsonify({"success": True, "message": f"Categoría '{categoria.nombre}' eliminada con éxito."}), 200
