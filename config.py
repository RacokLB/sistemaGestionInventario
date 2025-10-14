import os

class Config:
    # 1. Clave Secreta: DEBE provenir de una variable de entorno
    # '1722512287kk' se usa solo como un fallback local o en desarrollo
    SECRET_KEY = os.environ.get('SECRET_KEY') or '1722512287kk'
    
    # 2. Configuración de la Base de Datos (¡El cambio más importante!)
    
    # --- Configuración con Variables de Entorno ---
    
    # Obtener las variables necesarias del entorno
    DB_USER = os.environ.get('MYSQL_USER') or 'root'  # Fallback: 'root'
    DB_PASSWORD = os.environ.get('MYSQL_PASSWORD') or ''  # Fallback: vacío
    DB_HOST = os.environ.get('MYSQL_HOST') or 'localhost' # ¡Aquí estaba el problema!
    DB_PORT = os.environ.get('MYSQL_PORT') or '3306'      # Fallback: 3306
    DB_NAME = os.environ.get('MYSQL_DATABASE') or 'roberth' # Fallback: 'roberth'

    # Construye la URI de conexión usando las variables
    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    )
    
    # ---------------------------------------------

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 3. Directorio de Códigos de Barras (Ajuste recomendado para Docker)
    # Es mejor que esta ruta no dependa de __file__, sino de un WORKDIR fijo en el Dockerfile
    BARCODE_DIR = os.path.join(os.getcwd(), 'static', 'barcodes') 
    
    if not os.path.exists(BARCODE_DIR):
        os.makedirs(BARCODE_DIR)