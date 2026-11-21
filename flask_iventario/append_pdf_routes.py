@dropshipping_bp.route('/dropshipping/recibo/<int:id>')
@login_required
@rol_requerido('Administrador', 'Supervisor')
def recibo(id):
    import io
    from xhtml2pdf import pisa
    from flask import make_response
    
    orden = OrdenDropshipping.query.get_or_404(id)
    html_renderizado = render_template('dropshipping/recibo_pdf.html', orden=orden)
    
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_renderizado, dest=pdf_buffer)
    
    if pisa_status.err:
        flash("Hubo un error al generar el PDF.", "danger")
        return redirect(url_for('dropshipping.detalle', id=orden.id))
        
    response = make_response(pdf_buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=Recibo_Dropshipping_{orden.referencia}.pdf'
    return response

@dropshipping_bp.route('/dropshipping/reporte')
@login_required
@rol_requerido('Administrador', 'Supervisor')
def reporte():
    import io
    from xhtml2pdf import pisa
    from flask import make_response
    from datetime import datetime
    
    ordenes = OrdenDropshipping.query.order_by(OrdenDropshipping.fecha_creacion.desc()).all()
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    
    html_renderizado = render_template('dropshipping/reporte_pdf.html', ordenes=ordenes, fecha=fecha_actual)
    
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_renderizado, dest=pdf_buffer)
    
    if pisa_status.err:
        flash("Hubo un error al generar el reporte PDF.", "danger")
        return redirect(url_for('dropshipping.index'))
        
    response = make_response(pdf_buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=Reporte_Global_Dropshipping.pdf'
    return response
