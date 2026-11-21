from flask import Blueprint, render_template, request, flash, redirect, url_for
from models import Configuracion, db
from flask_login import login_required
from forms import ConfiguracionForm
from utils.decorators import rol_requerido

config_bp = Blueprint('configuracion', __name__)

@config_bp.route("/configuracion/marca", methods=["GET", "POST"])
@login_required
@rol_requerido('Administrador')
def marca():
    form = ConfiguracionForm()
    if request.method == "POST" and form.validate_on_submit():
        logo_url = form.logo_url.data
        favicon_url = form.favicon_url.data
        
        # Guardar Logo
        conf_logo = Configuracion.query.filter_by(clave="logo_url").first()
        if not conf_logo:
            conf_logo = Configuracion(clave="logo_url", descripcion="URL del Logo Principal")
            db.session.add(conf_logo)
        conf_logo.valor = logo_url
        
        # Guardar Favicon
        conf_fav = Configuracion.query.filter_by(clave="favicon_url").first()
        if not conf_fav:
            conf_fav = Configuracion(clave="favicon_url", descripcion="URL del Favicon")
            db.session.add(conf_fav)
        conf_fav.valor = favicon_url
        
        db.session.commit()
        flash("Identidad corporativa actualizada correctamente", "success")
        return redirect(url_for("configuracion.marca"))
        
    # GET: Cargar configuraciones actuales
    if request.method == "GET":
        logo = Configuracion.query.filter_by(clave="logo_url").first()
        favicon = Configuracion.query.filter_by(clave="favicon_url").first()
        form.logo_url.data = logo.valor if logo else ""
        form.favicon_url.data = favicon.valor if favicon else ""
    
    return render_template("config_marca.html", form=form, logo_url=form.logo_url.data, favicon_url=form.favicon_url.data)

# ==========================================
# GESTIÓN DE LISTAS DE PRECIOS
# ==========================================
@config_bp.route("/configuracion/listas-precios", methods=["GET"])
@login_required
@rol_requerido('Administrador', 'Supervisor')
def listas_precios():
    from models import ListasPrecios
    listas = ListasPrecios.query.order_by(ListasPrecios.id.asc()).all()
    return render_template("config_listas_precios.html", listas=listas)

@config_bp.route("/configuracion/listas-precios/crear", methods=["POST"])
@login_required
@rol_requerido('Administrador')
def crear_lista_precio():
    from models import ListasPrecios
    nombre = request.form.get("nombre")
    tipo = request.form.get("tipo")
    basado_en = request.form.get("basado_en")
    operador = request.form.get("operador")
    valor_regla = request.form.get("valor_regla")
    moneda = request.form.get("moneda", "USD")
    
    if not nombre:
        flash("El nombre es requerido.", "danger")
        return redirect(url_for("configuracion.listas_precios"))
        
    nueva_lista = ListasPrecios(
        nombre=nombre,
        tipo=tipo,
        basado_en=basado_en,
        operador=operador,
        valor_regla=float(valor_regla) if valor_regla else 0.00,
        moneda=moneda,
        activa=True
    )
    db.session.add(nueva_lista)
    db.session.commit()
    flash("Lista de precios creada exitosamente", "success")
    return redirect(url_for("configuracion.listas_precios"))

@config_bp.route("/configuracion/listas-precios/editar/<int:id>", methods=["POST"])
@login_required
@rol_requerido('Administrador')
def editar_lista_precio(id):
    from models import ListasPrecios
    lista = ListasPrecios.query.get_or_404(id)
    lista.nombre = request.form.get("nombre")
    lista.tipo = request.form.get("tipo")
    lista.basado_en = request.form.get("basado_en")
    lista.operador = request.form.get("operador")
    valor_regla = request.form.get("valor_regla")
    lista.valor_regla = float(valor_regla) if valor_regla else 0.00
    lista.moneda = request.form.get("moneda", "USD")
    lista.activa = 'activa' in request.form
    
    db.session.commit()
    flash("Lista de precios actualizada", "success")
    return redirect(url_for("configuracion.listas_precios"))

@config_bp.route("/configuracion/listas-precios/eliminar/<int:id>", methods=["POST"])
@login_required
@rol_requerido('Administrador')
def eliminar_lista_precio(id):
    from models import ListasPrecios
    lista = ListasPrecios.query.get_or_404(id)
    db.session.delete(lista)
    db.session.commit()
    flash("Lista de precios eliminada", "success")
    return redirect(url_for("configuracion.listas_precios"))


# ==========================================
# GESTIÓN DE MÓDULOS DEL SISTEMA
# ==========================================
@config_bp.route("/configuracion/modulos", methods=["GET", "POST"])
@login_required
@rol_requerido('Super Admin')
def modulos():
    conf_ds = Configuracion.query.filter_by(clave="modulo_dropshipping_activo").first()
    if not conf_ds:
        conf_ds = Configuracion(clave="modulo_dropshipping_activo", valor="false")
        db.session.add(conf_ds)
        db.session.commit()

    if request.method == "POST":
        nuevo_estado = "true" if request.form.get("modulo_dropshipping_activo") == "on" else "false"
        conf_ds.valor = nuevo_estado
        db.session.commit()
        estado_txt = "activado" if nuevo_estado == "true" else "desactivado"
        flash(f"Módulo de Dropshipping {estado_txt} correctamente.", "success")
        return redirect(url_for("configuracion.modulos"))

    ds_activo = (conf_ds.valor.lower() in ['true', '1', 'si'])
    return render_template("config_modulos.html", ds_activo=ds_activo)
