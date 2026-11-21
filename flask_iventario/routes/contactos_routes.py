from flask import Blueprint, request, flash, redirect, url_for, render_template, jsonify
from flask_login import current_user, login_required
from services.contactos_service import guardar_contacto, eliminar_contacto
from extensions import db
from models import Contactos, ListasPrecios
from forms import ContactosForm

contactos_bp = Blueprint("contactos", __name__)

@contactos_bp.before_request
def requerir_login():
    if not current_user.is_authenticated:
        flash("Debes iniciar sesión para acceder a esta página.", "warning")
        return redirect(url_for('auth.login'))

from models import GuiaDespacho, OrdenCompra, OrdenDropshipping

@contactos_bp.route("/contactos", methods=["GET"])
def index():
    q = request.args.get("q", "").strip()
    tipo_filtro = request.args.get("tipo", "todos")
    tasa_filtro = request.args.get("tasa", "todas")
    page = request.args.get("page", 1, type=int)

    query = Contactos.query.filter_by(deleted_at=None)

    if q:
        query = query.filter(
            db.or_(
                Contactos.nombre.ilike(f'%{q}%'),
                Contactos.identificacion.ilike(f'%{q}%'),
                Contactos.correo.ilike(f'%{q}%'),
                Contactos.ciudad.ilike(f'%{q}%')
            )
        )
        
    if tipo_filtro in ['clientes', 'cliente']:
        query = query.filter(Contactos.tipo.in_(['Cliente', 'Ambos']))
    elif tipo_filtro in ['proveedores', 'proveedor']:
        query = query.filter(Contactos.tipo.in_(['Proveedor', 'Ambos']))
    elif tipo_filtro == 'ambos':
        query = query.filter(Contactos.tipo == 'Ambos')
    elif tipo_filtro in ['usuarios', 'usuario']:
        query = query.filter(Contactos.tipo.in_(['Contacto Usuario', 'Usuario']))
    elif tipo_filtro in ['sin_definir', 'sin definir']:
        query = query.filter(Contactos.tipo.in_(['Sin Definir', None]))

    # Filtro por Tasa / Tarifa
    if tasa_filtro == 'sin_tarifa':
        query = query.filter(Contactos.lista_precio_id.is_(None))
    elif tasa_filtro and tasa_filtro != 'todas':
        try:
            lp_id = int(tasa_filtro)
            query = query.filter(Contactos.lista_precio_id == lp_id)
        except ValueError:
            query = query.join(Contactos.lista_precio).filter(
                db.or_(
                    ListasPrecios.moneda.ilike(f'%{tasa_filtro}%'),
                    ListasPrecios.nombre.ilike(f'%{tasa_filtro}%')
                )
            )
        
    contactos_paginados = query.order_by(Contactos.nombre.asc()).paginate(page=page, per_page=15, error_out=False)
    
    from models import Usuario, Rol
    usuarios = db.session.query(Usuario.username, Rol.nombre).join(Rol, Usuario.rol_id == Rol.id).all()
    usuarios_roles = {u[0].lower(): u[1] for u in usuarios if u[0]}
    
    for c in contactos_paginados.items:
        tipo_c = getattr(c, 'tipo', 'Cliente') or 'Cliente'
        c.es_cliente = (tipo_c in ['Cliente', 'Ambos'])
        c.es_proveedor = (tipo_c in ['Proveedor', 'Ambos'])
        c.es_usuario = (tipo_c in ['Contacto Usuario', 'Usuario'])
        c.es_sin_definir = (tipo_c in ['Sin Definir', None])
        c.rol_sistema = usuarios_roles.get(c.correo.lower()) if c.correo else None
    
    listas_precios = ListasPrecios.query.filter_by(activa=True).order_by(ListasPrecios.nombre.asc()).all()
    form = ContactosForm()
    form.lista_precio_id.choices = [(0, '-- Sin preferencia (Estándar de caja) --')] + [
        (lp.id, f"{lp.nombre} ({lp.moneda})") for lp in listas_precios
    ]
    
    return render_template("contactos.html", contactos=contactos_paginados, q=q, tipo_filtro=tipo_filtro, tasa_filtro=tasa_filtro, form=form, listas_precios=listas_precios)

@contactos_bp.route("/contactos/guardar", methods=["POST"])
def route_guardar_contacto():
    form = ContactosForm()
    listas_precios = ListasPrecios.query.filter_by(activa=True).order_by(ListasPrecios.nombre.asc()).all()
    form.lista_precio_id.choices = [(0, '-- Sin preferencia (Estándar de caja) --')] + [
        (lp.id, f"{lp.nombre} ({lp.moneda})") for lp in listas_precios
    ]
    if form.validate_on_submit():
        try:
            guardar_contacto(
                contacto_id=form.contacto_id.data,
                identificacion=form.identificacion.data,
                nombre=form.nombre.data,
                correo=form.correo.data,
                direccion=form.direccion.data,
                ciudad=form.ciudad.data,
                telefono=form.telefono.data,
                tipo=form.tipo.data if hasattr(form, 'tipo') and form.tipo.data else 'Cliente',
                lista_precio_id=form.lista_precio_id.data
            )
            flash("Contacto guardado con éxito.", "success")
        except ValueError as e:
            flash(str(e), "warning")
        except Exception as e:
            flash(f"Error inesperado al guardar: {str(e)}", "danger")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en {getattr(form, field).label.text}: {error}", "danger")
        
    return redirect(url_for("contactos.index"))

@contactos_bp.route("/api/contactos/crear", methods=["POST"])
def api_crear_contacto():
    data = request.get_json()
    try:
        identificacion = data.get('identificacion', '')
        nombre = data.get('nombre', '')
        
        if not identificacion or not nombre:
            return jsonify({'success': False, 'message': 'Rif/CI y Nombre son obligatorios'}), 400
            
        lp_id = None
        raw_lp = data.get('lista_precio_id')
        if raw_lp not in [None, '', 'base', 0, '0', 'None']:
            try:
                lp_id = int(raw_lp)
            except (ValueError, TypeError):
                lp_id = None

        contacto = Contactos(
            identificacion=identificacion,
            nombre=nombre,
            correo=data.get('correo') or None,
            direccion=data.get('direccion') or None,
            ciudad=data.get('ciudad') or None,
            telefono=data.get('telefono') or None,
            tipo=data.get('tipo', 'Cliente'),
            lista_precio_id=lp_id
        )
        db.session.add(contacto)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'contacto': {
                'id': contacto.id,
                'identificacion': contacto.identificacion,
                'nombre': contacto.nombre,
                'direccion': contacto.direccion,
                'ciudad': contacto.ciudad,
                'telefono': contacto.telefono,
                'correo': contacto.correo,
                'tipo': contacto.tipo,
                'lista_precio_id': contacto.lista_precio_id,
                'lista_precio_nombre': contacto.lista_precio.nombre if contacto.lista_precio else None,
                'lista_precio_moneda': contacto.lista_precio.moneda if contacto.lista_precio else None
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@contactos_bp.route("/contactos/generar_usuario/<int:id>", methods=["POST"])
def route_generar_usuario(id):
    if current_user.rol.nombre not in ['Super Admin', 'Administrador']:
        flash("Acceso denegado.", "danger")
        return redirect(url_for("contactos.index"))
        
    from models import Contactos, Rol
    from services.usuarios_service import guardar_usuario
    
    contacto = Contactos.query.get(id)
    if not contacto or not contacto.correo:
        flash("El contacto no existe o no tiene un correo configurado.", "danger")
        return redirect(url_for("contactos.index"))
        
    try:
        rol_cajero = Rol.query.filter_by(nombre="Cajero").first()
        if not rol_cajero:
            raise ValueError("El rol 'Cajero' no existe en el sistema.")
            
        guardar_usuario(
            usuario_id=None,
            username=contacto.correo.lower(),
            password="123456",
            rol_id=rol_cajero.id,
            activo=True
        )
        flash(f"Usuario {contacto.correo} generado con éxito. Su clave es 123456", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Error al generar usuario: {str(e)}", "danger")
        
    return redirect(url_for("contactos.index"))

@contactos_bp.route("/contactos/eliminar/<int:id>", methods=["POST"])
def route_eliminar_contacto(id):
    try:
        eliminar_contacto(id)
        flash("Contacto eliminado con éxito.", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Error al eliminar (posiblemente esté asociado a una venta): {str(e)}", "danger")
        
    return redirect(url_for("contactos.index"))

@contactos_bp.route("/api/contactos", methods=["GET"])
def api_obtener_contactos():
    contactos = Contactos.query.filter_by(deleted_at=None).all()
    lista_contactos = []
    for c in contactos:
        lista_contactos.append({
            "id": c.id,
            "nombre": c.nombre,
            "identificacion": c.identificacion,
            "direccion": c.direccion,
            "ciudad": c.ciudad,
            "telefono": c.telefono,
            "correo": c.correo,
            "tipo": getattr(c, 'tipo', 'Cliente') or 'Cliente',
            "lista_precio_id": c.lista_precio_id,
            "lista_precio_nombre": c.lista_precio.nombre if c.lista_precio else None,
            "lista_precio_moneda": c.lista_precio.moneda if c.lista_precio else None
        })
    return jsonify(lista_contactos)

@contactos_bp.route("/contactos/exportar_pdf")
@login_required
def exportar_pdf():
    import uuid
    import threading
    import os
    from flask import current_app, flash, redirect, url_for
    from flask_login import current_user, login_required
    
    q = request.args.get("q", "").strip()
    tipo_filtro = request.args.get("tipo", "todos")
    
    app_obj = current_app._get_current_object()
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"Reporte_Contactos_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
    
    def run_pdf_generation(app, fname, user_id, search_q, search_tipo):
        with app.app_context():
            from extensions import db
            from models import Contactos, GuiaDespacho, OrdenCompra, OrdenDropshipping, Notificacion
            import os
            from xhtml2pdf import pisa
            from flask import render_template
            
            try:
                query = Contactos.query.filter_by(deleted_at=None)

                if search_q:
                    query = query.filter(
                        db.or_(
                            Contactos.nombre.ilike(f'%{search_q}%'),
                            Contactos.identificacion.ilike(f'%{search_q}%'),
                            Contactos.correo.ilike(f'%{search_q}%')
                        )
                    )
                    
                if search_tipo in ['clientes', 'cliente']:
                    query = query.filter(Contactos.tipo.in_(['Cliente', 'Ambos']))
                elif search_tipo in ['proveedores', 'proveedor']:
                    query = query.filter(Contactos.tipo.in_(['Proveedor', 'Ambos']))
                elif search_tipo == 'ambos':
                    query = query.filter(Contactos.tipo == 'Ambos')
                elif search_tipo in ['usuarios', 'usuario']:
                    query = query.filter(Contactos.tipo.in_(['Contacto Usuario', 'Usuario']))
                elif search_tipo in ['sin_definir', 'sin definir']:
                    query = query.filter(Contactos.tipo.in_(['Sin Definir', None]))
                    
                lista_contactos = query.order_by(Contactos.nombre.asc()).all()
                
                for c in lista_contactos:
                    tipo_c = getattr(c, 'tipo', 'Cliente') or 'Cliente'
                    c.es_cliente = (tipo_c in ['Cliente', 'Ambos'])
                    c.es_proveedor = (tipo_c in ['Proveedor', 'Ambos'])
                    c.es_usuario = (tipo_c in ['Contacto Usuario', 'Usuario'])
                    c.es_sin_definir = (tipo_c in ['Sin Definir', None])

                fecha_actual = datetime.now().strftime("%d/%m/%Y")
                html_renderizado = render_template('pdf_contactos.html', 
                                                   contactos=lista_contactos, 
                                                   fecha=fecha_actual,
                                                   tipo_filtro=search_tipo)

                upload_folder = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                filepath = os.path.join(upload_folder, fname)
                
                with open(filepath, "w+b") as dest_pdf:
                    pisa_status = pisa.CreatePDF(html_renderizado, dest=dest_pdf)
                
                if pisa_status.err:
                    raise Exception("Error interno al generar PDF con xhtml2pdf")
                
                mensaje = f"El reporte de contactos está listo. <a href='/descargas/{fname}' target='_blank' class='fw-bold text-primary text-decoration-underline'>Descargar PDF</a>"
                notif = Notificacion(usuario_id=user_id, mensaje=mensaje, tipo='success')
            except Exception as e:
                print(f"Error generando PDF asincrono de contactos: {e}")
                notif = Notificacion(usuario_id=user_id, mensaje="Hubo un error al generar el PDF de contactos.", tipo='danger')
                
            db.session.add(notif)
            db.session.commit()
            
    t = threading.Thread(target=run_pdf_generation, args=(app_obj, filename, current_user.id, q, tipo_filtro))
    t.start()
    
    flash("El reporte en PDF se está generando en segundo plano. Recibirás una notificación en la campanita cuando esté listo para descargar.", "info")
    return redirect(url_for("contactos.index", q=q, tipo=tipo_filtro))

@contactos_bp.route("/contactos/exportar_excel")
@login_required
def exportar_excel():
    import pandas as pd
    import io
    from flask import send_file
    from datetime import datetime
    
    q = request.args.get("q", "").strip()
    tipo_filtro = request.args.get("tipo", "todos")
    tasa_filtro = request.args.get("tasa", "todas")
    
    query = Contactos.query.filter_by(deleted_at=None)

    if q:
        query = query.filter(
            db.or_(
                Contactos.nombre.ilike(f'%{q}%'),
                Contactos.identificacion.ilike(f'%{q}%'),
                Contactos.correo.ilike(f'%{q}%'),
                Contactos.ciudad.ilike(f'%{q}%')
            )
        )
        
    if tipo_filtro in ['clientes', 'cliente']:
        query = query.filter(Contactos.tipo.in_(['Cliente', 'Ambos']))
    elif tipo_filtro in ['proveedores', 'proveedor']:
        query = query.filter(Contactos.tipo.in_(['Proveedor', 'Ambos']))
    elif tipo_filtro == 'ambos':
        query = query.filter(Contactos.tipo == 'Ambos')
    elif tipo_filtro in ['usuarios', 'usuario']:
        query = query.filter(Contactos.tipo.in_(['Contacto Usuario', 'Usuario']))
    elif tipo_filtro in ['sin_definir', 'sin definir']:
        query = query.filter(Contactos.tipo.in_(['Sin Definir', None]))

    if tasa_filtro == 'sin_tarifa':
        query = query.filter(Contactos.lista_precio_id.is_(None))
    elif tasa_filtro and tasa_filtro != 'todas':
        try:
            lp_id = int(tasa_filtro)
            query = query.filter(Contactos.lista_precio_id == lp_id)
        except ValueError:
            query = query.join(Contactos.lista_precio).filter(
                db.or_(
                    ListasPrecios.moneda.ilike(f'%{tasa_filtro}%'),
                    ListasPrecios.nombre.ilike(f'%{tasa_filtro}%')
                )
            )
        
    lista_contactos = query.order_by(Contactos.nombre.asc()).all()
    
    from models import Usuario, Rol
    usuarios = db.session.query(Usuario.username, Rol.nombre).join(Rol, Usuario.rol_id == Rol.id).all()
    usuarios_roles = {u[0].lower(): u[1] for u in usuarios if u[0]}

    for c in lista_contactos:
        tipo_c = getattr(c, 'tipo', 'Cliente') or 'Cliente'
        c.es_cliente = (tipo_c in ['Cliente', 'Ambos'])
        c.es_proveedor = (tipo_c in ['Proveedor', 'Ambos'])
        c.es_usuario = (tipo_c in ['Contacto Usuario', 'Usuario'])
        c.es_sin_definir = (tipo_c in ['Sin Definir', None])
        c.rol_sistema = usuarios_roles.get(c.correo.lower()) if c.correo else None
        
    data = []
    for c in lista_contactos:
        tipo_str = []
        if c.es_cliente: tipo_str.append('Cliente')
        if c.es_proveedor: tipo_str.append('Proveedor')
        
        data.append({
            'Nombre / Razón Social': c.nombre,
            'RIF / CI': c.identificacion,
            'Correo': c.correo,
            'Teléfono': c.telefono,
            'Dirección': c.direccion,
            'Ciudad': c.ciudad if hasattr(c, 'ciudad') and c.ciudad else '',
            'Tipo': " - ".join(tipo_str) if tipo_str else "N/A",
            'Tasa / Tarifa Preferencial': f"{c.lista_precio.nombre} ({c.lista_precio.moneda})" if c.lista_precio else "Sin preferencia"
        })
        
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Contactos')
    output.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(
        output,
        download_name=f'Reporte_Contactos_{timestamp}.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
