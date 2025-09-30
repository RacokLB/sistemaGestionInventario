Aqui dejare una funcion para obtener la tasa del EUR Y el USD , usando la API pydolar, esto es un respaldo en caso de que el sevicio se recupere # La función para obtener la tasa del BCV, ahora corregida para siempre devolver una tupla.
def obtener_tasa_bcv(moneda_origen):
    """
    Obtiene la tasa de cambio del BCV para una moneda específica (USD o EUR)
    usando la API de PyDolarVenezuela.
    Retorna una tupla (Decimal(tasa), str(fecha)) o (None, None) si hay un error.
    """
    PYDOLARVENEZUELA_API_URL_USD = app.config['PYDOLARVENEZUELA_API_URL_USD']
    PYDOLARVENEZUELA_API_URL_EUR = app.config['PYDOLARVENEZUELA_API_URL_EUR']
   
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        if moneda_origen == 'USD':
            url = f"{PYDOLARVENEZUELA_API_URL_USD}bcv"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if 'price' in data:
                # El retorno exitoso siempre es una tupla de dos elementos
                return Decimal(str(data['price'])), data.get('last_update', 'N/A')
        elif moneda_origen == 'EUR':
            url = f"{PYDOLARVENEZUELA_API_URL_EUR}eur"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if 'price' in data:
                # El retorno exitoso siempre es una tupla de dos elementos
                return Decimal(str(data['price'])), data.get('last_update', 'N/A')
        else:
            print(f"ADVERTENCIA: Moneda {moneda_origen} no soportada.")
            return None, None

    except requests.exceptions.RequestException as req_err:
        print(f"Error al obtener tasa de {moneda_origen}: {req_err}")
    except (json.JSONDecodeError, KeyError) as parse_err:
        print(f"Error al parsear la respuesta JSON o llave no encontrada para {moneda_origen}: {parse_err}. Respuesta: {response.text}")
    except Exception as e:
        print(f"Error inesperado al obtener tasa de {moneda_origen}: {e}")
   
    # En caso de cualquier error, se retorna una tupla de dos elementos (None, None)
    # para evitar el TypeError al desempaquetar la respuesta.
    return None, None 





# barcode_utils.py
# Solución final para el error de fuente y el código de barras, compatible con PyInstaller

import io
import base64
import barcode
from barcode.writer import ImageWriter
from PIL import ImageFont
import os
import sys

# La lógica central para manejar las rutas de recursos en PyInstaller.
def resource_path(relative_path):
    """
    Obtiene la ruta absoluta de un recurso, compatible con PyInstaller.
    
    Cuando la aplicación está empaquetada, PyInstaller crea un directorio temporal
    y establece la variable sys._MEIPASS a esa ruta.
    """
    try:
        # Intenta usar la ruta temporal de PyInstaller
        base_path = sys._MEIPASS
    except Exception:
        # Si no está empaquetado, usa la ruta del directorio del script actual
        base_path = os.path.abspath(".")
        
    return os.path.join(base_path, relative_path)


def generar_codigo_barras_base64(valor):
    """
    Genera un código de barras en formato EAN-13 y lo devuelve como una
    cadena base64 para incrustar en HTML.
    
    Args:
        valor (int or str): El valor a codificar en el código de barras.
        
    Returns:
        str: Una cadena de imagen en formato base64.
    """
    try:
        # Asegurarse de que el valor sea una cadena de 12 dígitos
        valor_str = str(valor).zfill(12)
        
        # Opciones para el generador de código de barras
        opciones = dict(
            module_width=0.3,
            module_height=10,
            text_distance=5,
            font_size=8,
            quiet_zone=6.5
        )
        
        # Usa la función resource_path() para obtener la ruta correcta de la fuente
        font_path = resource_path(os.path.join('static', 'fonts', 'DejaVuSans.ttf'))
        print(f"Ruta de la fuente: {font_path}")
        
        # Verificar si la fuente existe. Esto es clave para evitar errores.
        if not os.path.exists(font_path):
            print(f"Advertencia: No se encontró la fuente en la ruta {font_path} La imagen se generará sin texto.")
            font = None
        else:
            # Si la fuente existe, cárgala.
            font = ImageFont.truetype(font_path, size=opciones['font_size'])
            
        # Crear el objeto ImageWriter y pasarle la fuente
        writer = ImageWriter()
        writer.font = font
        
        # Crear un objeto de código de barras
        cod_barras_obj = barcode.get_barcode_class('ean13')(valor_str, writer=writer)
        
        # Crear un buffer de bytes en memoria
        buffer = io.BytesIO()
        
        # Escribir la imagen del código de barras en el buffer
        cod_barras_obj.write(buffer, opciones)
        
        # Obtener los bytes y codificarlos en base64
        imagen_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        buffer.close()
        return imagen_base64
        
    except Exception as e:
        print(f"Error al generar el código de barras: {e}")
        return ""






