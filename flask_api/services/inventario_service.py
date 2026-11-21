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
            # (Si no tiene código ni precio, pero SÍ tiene nombre)
            if pd.isna(codigo) and pd.isna(precio) and not pd.isna(nombre):
                cat_nombre = str(nombre).strip()
                # Buscamos o creamos la categoría
                categoria_actual = Categorias.query.filter_by(nombre=cat_nombre).first()
                if not categoria_actual:
                    categoria_actual = Categorias(nombre=cat_nombre)
                    db.session.add(categoria_actual)
                    db.session.commit() # Guardamos para obtener su ID
                
                # Pasamos a la siguiente fila del Excel
                continue 

            # 4. Si no es categoría, es un producto. 
            # Validamos que no sea una fila totalmente vacía
            if pd.isna(nombre) or str(nombre).strip() == "":
                continue
            
            # Buscamos o creamos el VALOR de la Marca (Ej: "BOSCH", "TOYOTA")
            marca_nombre = str(marca_excel).strip() if not pd.isna(marca_excel) else "Genérica"
            valor_marca = ValoresAtributos.query.filter_by(atributo_id=attr_marca.id, valor=marca_nombre).first()
            if not valor_marca:
                valor_marca = ValoresAtributos(atributo_id=attr_marca.id, valor=marca_nombre)
                db.session.add(valor_marca)
                db.session.commit()

            # 5. Lógica de "Upsert" (Evitar duplicados)
            codigo_str = f"CÓDIGO: {codigo}" if not pd.isna(codigo) else ""
            nombre_limpio = str(nombre).strip()
            precio_float = float(precio) if not pd.isna(precio) else 0.0
            
            # Buscamos si el producto ya existe (usamos nombre y código como identificador único)
            producto_existente = Productos.query.filter_by(nombre=nombre_limpio, descripcion=codigo_str).first()
            
            if producto_existente:
                # Si existe, solo actualizamos el precio y la categoría
                producto_existente.precio = precio_float
                if categoria_actual:
                    producto_existente.categoria_id = categoria_actual.id
                
                # Nos aseguramos de que tenga su atributo (Marca)
                if valor_marca not in producto_existente.valores:
                    producto_existente.valores.append(valor_marca)
            else:
                # Si no existe, creamos un producto nuevo desde cero
                nuevo_producto = Productos(
                    nombre=nombre_limpio,
                    cantidad=10, # Asignamos 10 de stock como prueba inicial
                    precio=precio_float,
                    descripcion=codigo_str,
                    categoria_id=categoria_actual.id if categoria_actual else None
                )
                nuevo_producto.valores.append(valor_marca)
                db.session.add(nuevo_producto)
                productos_agregados += 1
            
        # Confirmamos todos los productos en la base de datos
        db.session.commit()
        return True, f"¡Éxito! Se detectaron categorías y se agregaron {productos_agregados} productos con sus atributos."
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error procesando el archivo: {str(e)}"
