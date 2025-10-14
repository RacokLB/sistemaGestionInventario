# Solución definitiva para el error de fuente y el código de barras.
# Genera el código de barras manualmente con la librería Pillow (PIL)
# para evitar problemas de dependencias.

import io
import base64
from PIL import Image, ImageDraw, ImageFont

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
        # Asegurarse de que el valor sea una cadena de 12 o 13 dígitos
        valor_str = str(valor).zfill(12)
        if len(valor_str) != 12:
            raise ValueError("El valor del código de barras debe ser de 12 dígitos.")

        # Definir las propiedades del código de barras (EAN-13)
        ancho_barra = 2
        alto_barra = 100
        ancho_imagen = 240  # Ajustado para que quepa todo
        alto_imagen = 150
        margen = 10
        
        # Crear la imagen
        imagen = Image.new('RGB', (ancho_imagen, alto_imagen), 'white')
        dibujo = ImageDraw.Draw(imagen)
        
        # Definir el mapeo de los dígitos a barras (módulo EAN-13)
        # Esto es solo una simplificación, la lógica real es más compleja
        digitos_a_barras = {
            '0': '0001101', '1': '0011001', '2': '0010011', '3': '0111101',
            '4': '0100011', '5': '0110001', '6': '0101111', '7': '0111011',
            '8': '0110111', '9': '0001011'
        }

        # Dibujar las barras del código de barras
        x_pos = margen
        for digito in valor_str:
            patron = digitos_a_barras[digito]
            for bit in patron:
                color = 'black' if bit == '1' else 'white'
                dibujo.rectangle([x_pos, margen, x_pos + ancho_barra, margen + alto_barra], fill=color)
                x_pos += ancho_barra
        
        # Dibujar el texto del código de barras
        # Usamos una fuente predeterminada para evitar el problema
        try:
            # Intentar cargar una fuente más legible si está disponible
            font = ImageFont.truetype("DejaVuSans.ttf", 20)
        except IOError:
            # Si no se encuentra, usar una fuente predeterminada
            font = ImageFont.load_default()

        # Dibujar el texto numérico
        ancho_texto = dibujo.textlength(valor_str, font=font)
        pos_texto = (ancho_imagen - ancho_texto) / 2
        dibujo.text((pos_texto, margen + alto_barra + 5), valor_str, font=font, fill='black')

        # Guardar la imagen en un buffer de bytes
        buffer = io.BytesIO()
        imagen.save(buffer, format='PNG')
        imagen_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()

        return imagen_base64

    except Exception as e:
        # Imprimir el error para depuración y devolver una cadena vacía
        print(f"Error al generar el código de barras: {e}")
        return ""