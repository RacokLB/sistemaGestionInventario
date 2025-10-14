# Archivo principal de la aplicación Flask
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config


#logging.basicConfig()
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO) # Set to INFO or DEBUG

#Cargar variables de entorno si existen
from dotenv import load_dotenv
load_dotenv()

#1. Initialize the flask app 
app = Flask(__name__)
# 2. Load the configuration from your Config class (THIS IS CRUCIAL!)
app.config.from_object(Config)

# 3. Initialize SQLAlchemy object WITHOUT passing the app yet
# This ensures 'db' exists before models try to import it.
db = SQLAlchemy()

#4. Explicitly link SQLAlchemy to the app using init_app
db.init_app(app)


#Importar los modelos y rutas 
from models import *
from routes import *

# Para inicializar la base de datos y crear las tablas
# Esto solo se ejecuta si el script se corre directamente
# y es crucial para crear las tablas en MySQL la primera vez.
with app.app_context():
    db.create_all()
    
    if __name__=='__main__':
        app.run(debug=False) # debug=True para desarrollo, cambiar a False en producción
        
        