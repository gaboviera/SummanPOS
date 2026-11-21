import os
import time
from flask import Flask

def limpiar_pdfs_antiguos(app: Flask):
    """
    Limpia los archivos PDF generados temporalmente que superan el tiempo
    de retención configurado en .env (RETENCION_PDF_DIAS, por defecto 1 día).
    """
    with app.app_context():
        try:
            dias_retencion = int(os.getenv("RETENCION_PDF_DIAS", "1"))
            segundos_retencion = dias_retencion * 24 * 60 * 60
            tiempo_actual = time.time()
            
            upload_folder = os.path.join(app.root_path, 'static', 'uploads')
            if not os.path.exists(upload_folder):
                return
                
            archivos_eliminados = 0
            
            for filename in os.listdir(upload_folder):
                if filename.startswith("Reporte_Inventario_") and filename.endswith(".pdf"):
                    filepath = os.path.join(upload_folder, filename)
                    # Comprobamos la edad del archivo (tiempo de modificación)
                    file_age = tiempo_actual - os.path.getmtime(filepath)
                    
                    if file_age > segundos_retencion:
                        os.remove(filepath)
                        archivos_eliminados += 1
                        print(f"[Cleanup] PDF eliminado: {filename}")
                        
            if archivos_eliminados > 0:
                print(f"[Cleanup] Se eliminaron {archivos_eliminados} PDFs antiguos.")
                
        except Exception as e:
            print(f"[Cleanup] Error limpiando PDFs: {str(e)}")
