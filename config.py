import os

class Config:
    # 1. Clave Secreta: DEBE provenir de una variable de entorno
    SECRET_KEY = os.environ.get('SECRET_KEY') or '1722512287kk'
    
    # 2. Configuración de la Base de Datos (PostgreSQL)
    
    # Opción A: Usar la variable de entorno estándar (e.g., proporcionada por Render)
    # Render, Heroku y otras plataformas inyectan una variable DATABASE_URL completa.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Opción B: Si DATABASE_URL no existe (entorno local o custom), construir la URI
    if SQLALCHEMY_DATABASE_URI is None:
        
        # Obtener las variables necesarias del entorno
        # Usamos prefijos 'POSTGRES' o 'PG' como es estándar.
        DB_USER = os.environ.get('PG_USER') or 'roberth_user'
        DB_PASSWORD = os.environ.get('PG_PASSWORD') or 'password_local'
        DB_HOST = os.environ.get('PG_HOST') or 'localhost' 
        DB_PORT = os.environ.get('PG_PORT') or '5432'  # Puerto estándar de PostgreSQL
        DB_NAME = os.environ.get('PG_DATABASE') or 'roberth_db'

        # Construye la URI de conexión para PostgreSQL usando psycopg2 como driver
        SQLALCHEMY_DATABASE_URI = (
            f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        )
    
    # ---------------------------------------------
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 3. Directorio de Códigos de Barras 
    # Mantenemos el uso de os.getcwd() para asegurar rutas relativas correctas en cualquier entorno
    BARCODE_DIR = os.path.join(os.getcwd(), 'static', 'barcodes') 
    
    if not os.path.exists(BARCODE_DIR):
        os.makedirs(BARCODE_DIR)
