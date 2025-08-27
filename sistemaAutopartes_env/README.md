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












