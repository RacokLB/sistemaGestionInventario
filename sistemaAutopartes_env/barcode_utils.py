import barcode
import io
import base64
from barcode.writer import ImageWriter
import os
from config import Config # Para obtener BARCODE_DIR

def generar_codigo_barras_base64(producto_id):
    """
    Genera un código de barras EAN13 para un producto y lo devuelve como una cadena Base64.
    Esto es ideal para incrustar directamente en HTML.
    """
    # EAN13 requiere 12 dígitos, generamos uno simple basado en el id
    # Rellenamos con ceros a la izquierda hasta 12 dígitos
    code_str = str(producto_id).zfill(12) 
    
    # Creamos un objeto EAN13 con un escritor de imágenes
    ean = barcode.EAN13(code_str, writer=ImageWriter())
    
    # Usamos un buffer en memoria en lugar de un archivo en disco
    buffer = io.BytesIO()
    ean.write(buffer)
    
    # Codificamos el contenido del buffer a Base64
    base64_img = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return base64_img