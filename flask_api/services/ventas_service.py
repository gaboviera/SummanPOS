import time
from datetime import datetime
from models import Productos, Transacciones, GuiaDespacho
from extensions import db
from services.contactos_service import asegurar_contacto_existente

def procesar_nueva_venta(cliente_data, carrito_data):
    """
    Procesa toda la lógica de negocio de una venta:
    1. Asegura que el contacto exista (o lo crea)
    2. Valida el stock
    3. Crea la Guía de Despacho
    4. Descuenta el inventario y crea las Transacciones
    """
    if not carrito_data or len(carrito_data) == 0:
        raise ValueError("El carrito está vacío.")

    # Generamos un código único usando la hora exacta, ej: VTA-17098453
    codigo_recibo = f"VTA-{int(time.time())}"

    # 1. Asegurar que el contacto exista (Lógica delegada al servicio de contactos)
    asegurar_contacto_existente(cliente_data)

    # 2. Guardar la Cabecera de la Guía de Despacho
    nueva_guia = GuiaDespacho(
        referencia=codigo_recibo,
        fecha=datetime.utcnow(),
        cliente_nombre=cliente_data.get('nombre'),
        cliente_identificacion=cliente_data.get('identificacion'),
        cliente_direccion=cliente_data.get('direccion'),
        cliente_telefono=cliente_data.get('telefono'),
        vendedor_nombre=cliente_data.get('vendedor'),
        observaciones=cliente_data.get('observaciones'),
        total=cliente_data.get('total', 0)
    )
    db.session.add(nueva_guia)

    # 3. Recorrer el Carrito y crear las transacciones
    for item in carrito_data:
        producto = Productos.query.get(item['id'])
        cantidad_vender = int(item['cantidad'])

        # Doble validación por seguridad
        if not producto or producto.cantidad < cantidad_vender:
            raise ValueError(f"Stock insuficiente para {producto.nombre if producto else 'desconocido'}")

        # Guardar la "foto" del stock actual ANTES de descontar
        stock_previo = producto.cantidad

        # Descontar del inventario maestro
        producto.cantidad -= cantidad_vender

        # Dejar huella en el historial de Transacciones
        nueva_transaccion = Transacciones(
            producto_id=producto.id,
            cantidad=cantidad_vender,
            fecha=datetime.utcnow(),
            tipo="Venta",
            stock_anterior=stock_previo,
            referencia=codigo_recibo
        )
        db.session.add(nueva_transaccion)

    # Confirmar todos los cambios (Contactos, Guia, Inventario, Transacciones)
    db.session.commit()
    
    return codigo_recibo
