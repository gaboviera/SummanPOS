from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from utils.decorators import rol_requerido
from services.categorias_service import obtener_categorias_paginadas, crear_categoria, editar_categoria, eliminar_categoria
from forms import CategoriasForm

categorias_bp = Blueprint('categorias', __name__, url_prefix='/categorias')

@categorias_bp.before_request
@login_required
def requerir_login():
    pass

@categorias_bp.route('/')
@rol_requerido('Administrador', 'Supervisor')
def listar():
    page = request.args.get('page', 1, type=int)
    query_str = request.args.get('q', '').strip()

    categorias = obtener_categorias_paginadas(page=page, query_str=query_str)
    
    form = CategoriasForm()
    
    return render_template('categorias.html', categorias=categorias, query_str=query_str, form=form)

@categorias_bp.route('/crear', methods=['POST'])
@rol_requerido('Administrador', 'Supervisor')
def crear():
    form = CategoriasForm()
    if form.validate_on_submit():
        nombre = form.nombre.data
        try:
            success, msg = crear_categoria(nombre)
            if success:
                flash(msg, "success")
            else:
                flash(msg, "warning")
        except ValueError as e:
            flash(str(e), "danger")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en {getattr(form, field).label.text}: {error}", "danger")
        
    return redirect(url_for('categorias.listar'))

@categorias_bp.route('/editar/<int:id>', methods=['POST'])
@rol_requerido('Administrador', 'Supervisor')
def editar(id):
    form = CategoriasForm()
    if form.validate_on_submit():
        nombre = form.nombre.data
        try:
            success, msg = editar_categoria(id, nombre)
            if success:
                flash(msg, "success")
            else:
                flash(msg, "danger")
        except ValueError as e:
            flash(str(e), "danger")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en {getattr(form, field).label.text}: {error}", "danger")
        
    return redirect(url_for('categorias.listar'))

@categorias_bp.route('/eliminar/<int:id>', methods=['POST'])
@rol_requerido('Administrador')
def eliminar(id):
    success, msg = eliminar_categoria(id)
    flash(msg, "success" if success else "danger")
    return redirect(url_for('categorias.listar'))
