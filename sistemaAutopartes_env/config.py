# Configuraciones de la aplicación
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '1722512287kk' # ¡Cambia esto en producción!
    
    # --- CAMBIO AQUÍ PARA MYSQL ---
    # Formato: mysql+pymysql://usuario:contraseña@host:puerto/nombre_base_datos
    # Por defecto en XAMPP, el usuario es 'root' y no hay contraseña.
    # El host es 'localhost' y el puerto es 3306.
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost:3306/roberth' # Cambia 'autopartes_db' por el nombre que le diste
    # Si tienes contraseña en tu usuario root de MySQL, sería:
    # SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:tu_contraseña@localhost:3306/autopartes_db'
    # -----------------------------

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BARCODE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'barcodes')
    # Asegúrate de que el directorio exista
    if not os.path.exists(BARCODE_DIR):
        os.makedirs(BARCODE_DIR)