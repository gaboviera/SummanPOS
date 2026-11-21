import pandas as pd
from extensions import db
from models import Productos, Categorias, Atributos, ValoresAtributos

def procesar_carga_masiva(archivo_storage):
    try:
        # header=None porque las primeras filas del excel original son fechas y espacios vacíos
        df = pd.read_excel(archivo_storage, header=None)
        
        # 1. Aseguramos que el Atributo Maestro "Marca" exista (Estilo Odoo)
        attr_marca = Atributos.query.filter_by(nombre="Marca").first()
        if not attr_marca:
            attr_marca = Atributos(nombre="Marca")
            db.session.add(attr_marca)
            db.session.commit()

        # CACHÉ PARA OPTIMIZAR QUERIES
        categorias_cache = {c.nombre: c for c in Categorias.query.all()}
        valores_marca_cache = {v.valor: v for v in ValoresAtributos.query.filter_by(atributo_id=attr_marca.id).all()}
        # Opcional: Cachear productos para evitar query por cada fila (acelera enormemente)
        productos_cache = {(p.nombre, p.descripcion): p for p in Productos.query.all()}

        categoria_actual = None
        productos_agregados = 0

        # 2. Iteramos saltando las primeras 4 filas (0, 1, 2, 3) que son los títulos del Excel
        for index, fila in df.iloc[4:].iterrows():
            
            # --- LÍNEA DE SEGURIDAD ---
            if str(fila[3]).strip().upper() == 'PRECIO':
                continue
            # ---------------------------
            # Según tu Excel original:
            # Col 0: CÓDIGO | Col 1: MARCA | Col 2: NOMBRE | Col 3: PRECIO
            codigo = fila[0]
            marca_excel = fila[1]
            nombre = fila[2]
            precio = fila[3]

            # 3. ¿Es un título de Categoría anidado?
            if pd.isna(codigo) and pd.isna(precio) and not pd.isna(nombre):
                cat_nombre = str(nombre).strip()
                if cat_nombre not in categorias_cache:
                    categoria_actual = Categorias(nombre=cat_nombre)
                    db.session.add(categoria_actual)
                    db.session.flush() # flush en vez de commit para obtener ID rápido
                    categorias_cache[cat_nombre] = categoria_actual
                else:
                    categoria_actual = categorias_cache[cat_nombre]
                continue 

            # 4. Si no es categoría, es un producto. 
            if pd.isna(nombre) or str(nombre).strip() == "":
                continue
            
            # Buscamos o creamos el VALOR de la Marca
            marca_nombre = str(marca_excel).strip() if not pd.isna(marca_excel) else "Genérica"
            if marca_nombre not in valores_marca_cache:
                valor_marca = ValoresAtributos(atributo_id=attr_marca.id, valor=marca_nombre)
                db.session.add(valor_marca)
                db.session.flush()
                valores_marca_cache[marca_nombre] = valor_marca
            else:
                valor_marca = valores_marca_cache[marca_nombre]

            # 5. Lógica de "Upsert" (Evitar duplicados)
            codigo_str = f"CÓDIGO: {codigo}" if not pd.isna(codigo) else ""
            nombre_limpio = str(nombre).strip()
            precio_float = float(precio) if not pd.isna(precio) else 0.0
            
            # Buscamos si el producto ya existe desde la caché
            producto_existente = productos_cache.get((nombre_limpio, codigo_str))
            
            if producto_existente:
                # Si existe, solo actualizamos el precio y la categoría
                producto_existente.precio = precio_float
                if categoria_actual:
                    producto_existente.categoria_id = categoria_actual.id
                
                # Nos aseguramos de que tenga su atributo (Marca)
                if valor_marca not in producto_existente.valores:
                    producto_existente.valores.append(valor_marca)
            else:
                # Si no existe, creamos un producto nuevo
                nuevo_producto = Productos(
                    nombre=nombre_limpio,
                    cantidad=10, # Asignamos 10 de stock inicial
                    precio=precio_float,
                    descripcion=codigo_str,
                    categoria_id=categoria_actual.id if categoria_actual else None
                )
                nuevo_producto.valores.append(valor_marca)
                db.session.add(nuevo_producto)
                productos_cache[(nombre_limpio, codigo_str)] = nuevo_producto
                productos_agregados += 1
            
            # Commit en lotes para evitar sobrecarga de memoria
            if index % 500 == 0:
                db.session.commit()
            
        # Confirmamos todos los productos en la base de datos
        db.session.commit()
        return True, f"¡Éxito! Se detectaron categorías y se agregaron {productos_agregados} productos con sus atributos."
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error procesando el archivo: {str(e)}"

def obtener_historial_filtrado(filtros, page):
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func
    from datetime import datetime
    from models import Transacciones, Productos
    from extensions import db
    from flask import flash
    
    q = filtros.get('q', '').strip()
    fecha_inicio = filtros.get('fecha_inicio', '').strip()
    fecha_fin = filtros.get('fecha_fin', '').strip()
    tipo = filtros.get('tipo', '').strip()
    
    query = Transacciones.query.join(Productos).options(joinedload(Transacciones.producto))
    
    if q:
        query = query.filter(db.or_(
            Transacciones.referencia.ilike(f'%{q}%'),
            Productos.nombre.ilike(f'%{q}%')
        ))
        
    if fecha_inicio:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            query = query.filter(func.date(Transacciones.fecha) >= fecha_inicio_dt.date())
        except ValueError:
            flash("El formato de la fecha de inicio es incorrecto (debe ser AAAA-MM-DD).", "danger")
            
    if fecha_fin:
        try:
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            query = query.filter(func.date(Transacciones.fecha) <= fecha_fin_dt.date())
        except ValueError:
            flash("El formato de la fecha de fin es incorrecto (debe ser AAAA-MM-DD).", "danger")
            
    if tipo:
        query = query.filter(Transacciones.tipo == tipo)
        
    return query.order_by(Transacciones.id.desc()).paginate(page=page, per_page=50, error_out=False)
