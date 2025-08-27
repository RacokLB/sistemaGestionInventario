from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app, db
from config import *
from models import Producto, Categoria, PiezaGenerica ,Proveedor, Cliente, Compra, DetalleCompra, Venta, DetalleVenta, Marca, Modelo, TasaCambio, Role, User, ActivityLog
from forms import ProductoForm, DetalleCompraForm,CompraForm, ProveedorForm , CompraForm, VentaForm, ClienteForm, ProveedorForm, DetalleVentaForm , LoginForm, RegistrationForm # Tus formularios
from barcode_utils import generar_codigo_barras_base64 # Tu función de código de barras
from sqlalchemy import func, desc, and_ # Para usar funciones SQL como SUM
# Ejemplo conceptual con WeasyPrint (requiere pip install weasyprint)
from flask import render_template
from decimal import Decimal, ROUND_HALF_UP
import json
import requests
import datetime
from datetime import *
from datetime import date
from wtforms import ValidationError
import io
import base64
import barcode
from barcode.writer import ImageWriter
from models import TasaCambio
from flask_login import login_user, login_required, logout_user, current_user, LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    #Autenticacion del usuario
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    """Ruta para registrar nuevos usuarios."""
    form = RegistrationForm()
    if form.validate_on_submit():
        # Hashear la contraseña antes de guardarla
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        
        # Asignar un rol por defecto (por ejemplo, 'user')
        default_role = Role.query.filter_by(name='user').first()
        if not default_role:
            # Si el rol no existe, créalo
            default_role = Role(name='user')
            db.session.add(default_role)
            db.session.commit()

        # Crear el nuevo usuario
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_password,
            role=default_role
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('¡Registro exitoso! Por favor, inicia sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar el usuario: {str(e)}', 'danger')
    return render_template('auth/register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    #Autenticacion del usuario
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    """Ruta para el inicio de sesión."""
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash('¡Has iniciado sesión exitosamente!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos. Por favor, inténtalo de nuevo.', 'danger')
    return render_template('auth/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Ruta para cerrar sesión."""
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('index'))


def obtener_tasas_ultimos_30_dias():
    """
    Función que consulta la base de datos para obtener las tasas de cambio
    de los últimos 30 días.
    
    Retorna:
        (list, list): Una tupla de listas, una con las tasas y otra con las fechas.
    """
    treinta_dias_atras = datetime.now() - timedelta(days=30)
    
    # Consulta la base de datos para obtener las tasas y las fechas
    tasas_historicas = db.session.query(TasaCambio).filter(
        TasaCambio.fecha >= treinta_dias_atras
    ).order_by(TasaCambio.fecha).all()
    
    tasas = [float(tasa.tasa) for tasa in tasas_historicas]
    fechas = [tasa.fecha.strftime('%Y-%m-%d') for tasa in tasas_historicas]
        
    return tasas, fechas

# --- Función de ayuda para registrar actividades ---
def log_activity(action, details=None):
    """
    Registra una acción del usuario en la base de datos.
    
    Args:
        action (str): La descripción de la acción (ej. 'Inicio de sesión exitoso').
        details (str, opcional): Detalles adicionales sobre la acción.
    """
    if current_user.is_authenticated:
        log = ActivityLog(user_id=current_user.id, action=action, details=details)
        db.session.add(log)
        db.session.commit()

@app.route('/dashboard')
@login_required
def dashboard():
    # --- Lógica para el filtro de tiempo ---
    # Obtener las fechas del formulario (si existen)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Inicializar listas de filtros separadas para ventas y compras
    ventas_filtro = []
    compras_filtro = []
    start_date = None
    end_date = None

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            ventas_filtro.append(Venta.fecha_venta >= start_date)
            compras_filtro.append(Compra.fecha_compra >= start_date)
        except ValueError:
            # Manejar el error si la fecha no es válida, quizás con un mensaje flash
            pass
            
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            # Se agrega un día para incluir la fecha final completa
            end_date = end_date.replace(hour=23, minute=59, second=59)
            ventas_filtro.append(Venta.fecha_venta <= end_date)
            compras_filtro.append(Compra.fecha_compra <= end_date)
        except ValueError:
            pass

    # --- Métricas Principales (Ahora con filtros específicos) ---
    
    # total_ventas_bs: Aplica el filtro de fecha de ventas
    total_ventas_bs = db.session.query(
        func.sum(Venta.total_venta_bs)
    ).filter(*ventas_filtro).scalar()
    total_ventas_bs = total_ventas_bs if total_ventas_bs is not None else 0.00
    total_ventas_bs = Decimal(total_ventas_bs)
    
    # total_ventas: Aplica el filtro de fecha de ventas
    total_ventas = db.session.query(
        func.sum(Venta.total_venta_divisa)
    ).filter(*ventas_filtro).scalar()
    total_ventas = total_ventas if total_ventas is not None else 0.00
    total_ventas = Decimal(total_ventas)

    # total_compras: Aplica el filtro de fecha de compras
    total_compras = db.session.query(
        func.sum(DetalleCompra.cantidad * DetalleCompra.precio_adquisicion)
    ).join(Compra).filter(*compras_filtro).scalar()
    total_compras = total_compras if total_compras is not None else 0.00
    
    # --- Métricas de Inventario (NO aplican filtro de tiempo) ---
    valor_inventario = db.session.query(
        func.sum(Producto.stock * Producto.precio_venta)
    ).scalar()
    valor_inventario = valor_inventario if valor_inventario is not None else 0.00
    
    cantidad_total_stock = db.session.query(func.sum(Producto.stock)).scalar()
    cantidad_total_stock = cantidad_total_stock if cantidad_total_stock is not None else 0

    # --- Productos más vendidos (Aplica filtro de fecha de ventas) ---
    productos_mas_vendidos = db.session.query(
        Producto.descripcion,
        func.sum(DetalleVenta.cantidad).label('total_vendido')
    ).join(DetalleVenta).join(Venta).filter(*ventas_filtro).group_by(
        Producto.id, Producto.descripcion
    ).order_by(desc('total_vendido')).limit(5).all()

    # --- Productos bajo stock (NO aplica filtro de tiempo) ---
    UMBRAL_BAJO_STOCK = 10 
    productos_bajo_stock = db.session.query(
        Producto.descripcion,
        Producto.stock,
        Marca.nombre.label('marca_vehiculo_nombre'),
        Modelo.nombre.label('modelo_vehiculo_nombre')
    ).join(Marca, Producto.id_marca_vehiculo == Marca.id) \
     .join(Modelo, Producto.id_modelo_vehiculo == Modelo.id) \
     .filter(Producto.stock < UMBRAL_BAJO_STOCK) \
     .order_by(Producto.stock, Producto.descripcion).all()

    # --- Cálculo de la ganancia bruta (Aplica filtro de fecha de ventas) ---
    # Para el costo de ventas, también debemos filtrar por fecha de venta
    subquery_last_acquisition_price = db.session.query(
        DetalleCompra.producto_id,
        DetalleCompra.precio_adquisicion,
        func.row_number().over(
            partition_by=DetalleCompra.producto_id,
            order_by=desc(DetalleCompra.id) 
        ).label('rn')
    ).subquery()
    
    costo_ventas = db.session.query(
        func.sum(DetalleVenta.cantidad * subquery_last_acquisition_price.c.precio_adquisicion)
    ).join(Venta).filter(*ventas_filtro).join(subquery_last_acquisition_price, and_(
        DetalleVenta.producto_id == subquery_last_acquisition_price.c.producto_id,
        subquery_last_acquisition_price.c.rn == 1 
    )).scalar()
    
    costo_ventas = costo_ventas if costo_ventas is not None else 0.00
    costo_ventas = Decimal(costo_ventas)
    ganancia_bruta = total_ventas - costo_ventas

    # --- Productos menos vendidos (Aplica filtro de fecha de ventas) ---
    productos_con_ventas = db.session.query(
        Producto.id,
        func.sum(DetalleVenta.cantidad).label('total_vendido')
    ).outerjoin(DetalleVenta).join(Venta).filter(*ventas_filtro).group_by(
        Producto.id
    ).subquery() 
    
    productos_menos_vendidos = db.session.query(
        Producto.descripcion,
        productos_con_ventas.c.total_vendido
    ).outerjoin(productos_con_ventas, Producto.id == productos_con_ventas.c.id) \
     .order_by(productos_con_ventas.c.total_vendido, Producto.descripcion) \
     .limit(5).all()

    # Obtener las tasas de cambio (sin filtro de tiempo, según tu petición)
    tasa_bcv, fecha_usd = obtener_tasa_bcv('USD')
    #tasa_eur_compra, tasa_eur_venta, fecha_eur = obtener_tasa_bcv('EUR')

    # Lógica para obtener las tasas de cambio para el gráfico
    tasas_usd_ultimos_30_dias, fechas_ultimos_30_dias = obtener_tasas_ultimos_30_dias()

    # Pasa todas las métricas y las tasas a la plantilla, incluyendo las fechas del filtro
    return render_template('dashboard.html',
        total_ventas=f"{total_ventas:.2f}",
        total_compras=f"{total_compras:.2f}",
        valor_inventario=f"{valor_inventario:.2f}",
        cantidad_total_stock=cantidad_total_stock,
        total_ventas_bs=f"{total_ventas_bs:.2f}",
        productos_mas_vendidos=productos_mas_vendidos,
        productos_bajo_stock=productos_bajo_stock,
        ganancia_bruta=f"{ganancia_bruta:.2f}", 
        productos_menos_vendidos=productos_menos_vendidos,
        tasa_bcv=tasa_bcv, 
        fecha_usd=fecha_usd, 
        #tasa_eur_venta=tasa_eur_venta, 
        #fecha_eur=fecha_eur,
        start_date=start_date_str, # Se pasa al template para que se mantenga el valor
        end_date=end_date_str,
        # Nuevas variables para el gráfico
        tasas_usd_ultimos_30_dias=tasas_usd_ultimos_30_dias,
        fechas_ultimos_30_dias=fechas_ultimos_30_dias
    )
# Nueva ruta para renderizar la página de consulta de piezas
@app.route('/consultar_piezas')
def consultar_piezas():
    return render_template('consultar_piezas.html')

# --- Configuración de la API de Gemini ---
# IMPORTANTE: Reemplaza "" con tu clave de API de Gemini REAL.
# Para aplicaciones en producción, considera usar variables de entorno
# para almacenar tu clave de API de forma segura.
API_KEY = "AIzaSyBzb08WuAJdKbXs1AnQpfDZVBJ7KfVdwP4" # Asegúrate de reemplazar esto con tu clave de API de Gemini REAL.
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"

# --- Configuración para retroceso exponencial ---
MAX_RETRIES = 5
INITIAL_DELAY = 1  # segundos

@app.route('/api/consulta', methods=['POST'])
def api_consulta():
    """
    Maneja las solicitudes de consulta de piezas, llamando a la API de Google Gemini.
    """
    request_data = request.get_json()
    user_prompt = request_data.get('prompt')

    # --- LÍNEA PARA DEPURACIÓN ---
    print(f"Prompt de usuario recibido en el backend: '{user_prompt}'")
    # ----------------------------------

    if not user_prompt:
        return jsonify({"error": "No se proporcionó un prompt."}), 400

    # --- MODIFICACIÓN CLAVE AQUÍ ---
    # Se añade un prefijo al prompt para guiar al modelo a dar una respuesta más detallada.
    # También se aumenta maxOutputTokens para darle más espacio para generar la respuesta.
    full_prompt = f"Como un experto en autopartes, por favor, proporciona una respuesta corte y precisa sobre la siguiente pieza, incluyendo posibles números de parte y compatibilidad con otro vehiculo.: {user_prompt}"
    # -------------------------------

    # Construir el payload para la API de Gemini
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": full_prompt}] # Usamos el prompt enriquecido
            }
        ],
        "generationConfig": {
            "temperature": 0.4,  # Ajusta la creatividad de la respuesta (0.0 a 1.0)
            "topP": 0.95,
            "topK": 40
            
        }
    }

    retries = 0
    while retries < MAX_RETRIES:
        try:
            # Realizar la llamada a la API de Gemini
            response = requests.post(f"{GEMINI_API_URL}?key={API_KEY}", json=payload)
            response.raise_for_status()  # Lanza una excepción para códigos de estado HTTP erróneos (4xx o 5xx)
            
            gemini_data = response.json()
            print(f"Respuesta completa recibida de Gemini: {gemini_data}") # Esto ya estaba, pero es clave.

            # Extraer la respuesta del modelo
            if gemini_data and 'candidates' in gemini_data and gemini_data['candidates']:
                first_candidate = gemini_data['candidates'][0]
                if 'content' in first_candidate and 'parts' in first_candidate['content']:
                    response_text = first_candidate['content']['parts'][0]['text']
                    return jsonify({"respuesta": response_text})
            else:
                # Si no hay candidatos o la estructura es inesperada
                print(f"Error: Estructura de respuesta inesperada de Gemini. No se encontraron 'candidates' o 'content': {gemini_data}")
                return jsonify({"error": "No se pudo obtener una respuesta válida del modelo. Estructura inesperada."}), 500

        except requests.exceptions.HTTPError as http_err:
            print(f"Error HTTP: {http_err} - Código de estado: {http_err.response.status_code} - Respuesta: {http_err.response.text}")
            if http_err.response.status_code in [429, 500, 503]: # Errores reintentables: Too Many Requests, Internal Server Error, Service Unavailable
                delay = INITIAL_DELAY * (2 ** retries)
                print(f"Reintentando en {delay} segundos...")
                time.sleep(delay)
                retries += 1
            else:
                # Otros errores HTTP no reintentables
                return jsonify({"error": f"Error de la API de Gemini: {http_err.response.status_code} - {http_err.response.text}"}), http_err.response.status_code
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Error de conexión: {conn_err}")
            delay = INITIAL_DELAY * (2 ** retries)
            print(f"Reintentando en {delay} segundos...")
            time.sleep(delay)
            retries += 1
        except requests.exceptions.Timeout as timeout_err:
            print(f"Error de tiempo de espera: {timeout_err}")
            delay = INITIAL_DELAY * (2 ** retries)
            print(f"Reintentando en {delay} segundos...")
            time.sleep(delay)
            retries += 1
        except Exception as e:
            print(f"Ocurrió un error inesperado: {e}")
            return jsonify({"error": f"Ocurrió un error inesperado al procesar la solicitud: {e}"}), 500

    # Si se agotan los reintentos
    return jsonify({"error": "La solicitud falló después de varios reintentos. Por favor, intenta de nuevo más tarde."}), 500

## Rutas para Productos
@app.route('/productos')
@login_required
def listar_productos():
    """
    Muestra una lista de todos los productos activos.
    """
    #Se obtiene solo los productos que estan activos
    productos = db.session.query(Producto).filter_by(is_active=True).all()
    return render_template('productos/listar.html', productos=productos)

# --- Nueva Ruta API para Obtener Categoria & Piezas ---
@app.route('/api/categoria_de_pieza/', methods=['GET'])
def get_categoria_de_pieza():
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    categoria_data = [{'id': categoria.id, 'nombre': categoria.nombre} for categoria in categorias]
    return jsonify(categoria_data)

@app.route('/api/piezas_por_categoria/<int:categoria_id>', methods=['GET'])
def get_piezas_por_categoria(categoria_id):
    piezas = PiezaGenerica.query.filter_by(id_categoria=categoria_id).order_by(PiezaGenerica.nombre).all()
    piezas_data = [{'id': p.id, 'nombre': p.nombre} for p in piezas]
    return jsonify(piezas_data)

# --- FIN Rutas para Categoria & Pieza ---
@app.route('/api/marcas_vehiculo/', methods=['GET'])
def get_marcas_vehiculo():
    marcas = Marca.query.order_by(Marca.nombre).all()
    marca_data = [{'id': marca.id, 'nombre': marca.nombre} for marca in marcas]
    return jsonify(marca_data)

# --- Nueva Ruta API para Obtener Modelos por Marca ---
@app.route('/api/modelos_por_marca/<int:marca_id>', methods=['GET'])
def get_modelos_por_marca(marca_id):
    modelos = Modelo.query.filter_by(id_marca=marca_id).order_by(Modelo.nombre).all()
    modelos_data = [{'id': modelo.id, 'nombre': modelo.nombre} for modelo in modelos]
    return jsonify(modelos_data)
# --- FIN Rutas para Marcas y Modelos ---

# --- Nueva Ruta API para filtrar Productos ---
# ** when u need to call a fetch from frontend the way u have to do is this /api/productos_filtrados?${variable with a value into her}
@app.route('/api/productos_filtrados', methods=['GET'])
def get_productos_filtrados():
    # Obtener los parámetros de la URL
    marca_id = request.args.get('marca_id', type=int)
    modelo_id = request.args.get('modelo_id', type=int)
    categoria_id = request.args.get('categoria_id', type=int)
    pieza_id = request.args.get('pieza_id', type=int)

    # Iniciar la consulta de productos
    query = Producto.query

    # Aplicar filtros si los parámetros están presentes
    if marca_id:
        query = query.filter_by(id_marca_vehiculo=marca_id)
        print(f" Este es el ID de la marca vehiculo: {marca_id}")
    if modelo_id:
        query = query.filter_by(id_modelo_vehiculo=modelo_id)
        print(f" Este es el ID del modelo del vehiculo: {modelo_id}")
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
        print(f" Este es el ID de la categoria de las piezas: {categoria_id}")
    if pieza_id:
        query = query.filter_by(pieza_generica_id=pieza_id)
        print(f"Este es el id de las piezas {pieza_id}")

    # Ejecutar la consulta y obtener los productos
    productos = query.order_by(Producto.descripcion).all()
    
    # Formatear los productos para la respuesta JSON
    productos_data = [{
        'id': p.id,
        'descripcion': p.descripcion,
        'marca_repuesto': p.marca_repuesto,
        'categoria_id':p.categoria_id,
        'pieza_generica_id':p.pieza_generica_id,
        'marca_vehiculo':p.marca_vehiculo.nombre,
        'modelo_vehiculo':p.modelo_vehiculo.nombre,
        'generacion':p.generacion,
        'precio_compra':str(p.precio_compra),
        'precio_venta': str(p.precio_venta), # Convertir a string para evitar errores de serialización
        'stock': p.stock,
        'ubicacion': p.ubicacion,
        
    } for p in productos]
    
    print(f"Productos filtrados {productos_data}")
    return jsonify(productos_data)
    

# --- Route for creating products ---
@app.route('/productos/crear', methods=['GET', 'POST'])
@login_required
def crear_producto():
    form = ProductoForm()

    # --- Populate choices for ALL SelectFields initially (GET and POST) ---
    categorias_piezas = Categoria.query.order_by(Categoria.nombre).all()
    form.categoria_id.choices = [(c.id, c.nombre) for c in categorias_piezas]
    if not form.categoria_id.choices or form.categoria_id.choices[0][0] != 0:
        form.categoria_id.choices.insert(0, (0, 'Selecciona una categoría'))

    marcas_vehiculos = Marca.query.order_by(Marca.nombre).all()
    form.id_marca_vehiculo.choices = [(m.id, m.nombre) for m in marcas_vehiculos]
    if not form.id_marca_vehiculo.choices or form.id_marca_vehiculo.choices[0][0] != 0:
        form.id_marca_vehiculo.choices.insert(0, (0, 'Selecciona una marca'))
    
    selected_categoria_id = form.categoria_id.data if request.method == 'POST' else None
    if selected_categoria_id and selected_categoria_id != 0:
        piezas_por_categoria = PiezaGenerica.query.filter_by(id_categoria=selected_categoria_id).order_by(PiezaGenerica.nombre).all()
        form.pieza_id.choices = [(p.id, p.nombre) for p in piezas_por_categoria]
    else:
        form.pieza_id.choices = [] 
    if not form.pieza_id.choices or form.pieza_id.choices[0][0] != 0:
        form.pieza_id.choices.insert(0, (0, 'Selecciona una pieza'))

    selected_marca_vehiculo_id = form.id_marca_vehiculo.data if request.method == 'POST' else None
    if selected_marca_vehiculo_id and selected_marca_vehiculo_id != 0:
        modelos_por_marca = Modelo.query.filter_by(id_marca=selected_marca_vehiculo_id).order_by(Modelo.nombre).all()
        form.id_modelo_vehiculo.choices = [(m.id, m.nombre) for m in modelos_por_marca]
    else:
        form.id_modelo_vehiculo.choices = [] 
    if not form.id_modelo_vehiculo.choices or form.id_modelo_vehiculo.choices[0][0] != 0:
        form.id_modelo_vehiculo.choices.insert(0, (0, 'Selecciona un modelo'))


    if form.validate_on_submit():
        try:
            nuevo_producto = Producto(
                categoria_id=form.categoria_id.data,
                pieza_generica_id=form.pieza_id.data, 
                descripcion=form.descripcion.data,
                marca_repuesto=form.marca_repuesto.data,
                id_marca_vehiculo=form.id_marca_vehiculo.data, 
                id_modelo_vehiculo=form.id_modelo_vehiculo.data,
                generacion=form.generacion.data,
                precio_compra=form.precio_compra.data,
                precio_venta=form.precio_venta.data,
                stock=form.stock.data,
                ubicacion=form.ubicacion.data,
                # El campo codigo_barras_base64 se asignará después
            )
            
            db.session.add(nuevo_producto)
            db.session.flush() # Obtiene el ID del nuevo producto

            if nuevo_producto.id:
                # Usamos la función optimizada que devuelve la cadena Base64
                base64_img = generar_codigo_barras_base64(nuevo_producto.id)
                nuevo_producto.codigo_barras_base64 = base64_img
            
            db.session.commit()
            # --- Registrar la actividad de creación de producto ---
            log_activity(action="Producto creado", details=f"Producto: {form.descripcion.data}")

            flash('Producto creado exitosamente.', 'success')
            return redirect(url_for('listar_productos'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al registrar el producto: {str(e)}', 'danger')
            
    return render_template('productos/crear.html', form=form)


@app.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_producto(id):
    producto = Producto.query.filter_by(id=id).first_or_404()
    form = ProductoForm(obj=producto) # WTForms loads product data into form fields

    # --- Populate choices for ALL SelectFields initially (for GET and POST re-render) ---

    # 1. Categoria de la Pieza (Parent Selector)
    categorias_piezas = Categoria.query.order_by(Categoria.nombre).all()
    form.categoria_id.choices = [(c.id, c.nombre) for c in categorias_piezas]
    # Ensure a default '0' option is present if not already from previous processing
    if not form.categoria_id.choices or form.categoria_id.choices[0][0] != 0:
        form.categoria_id.choices.insert(0, (0, 'Selecciona una categoría'))

    # 2. Marca del Vehículo (Parent Selector)
    marcas_vehiculos = Marca.query.order_by(Marca.nombre).all()
    form.id_marca_vehiculo.choices = [(m.id, m.nombre) for m in marcas_vehiculos]
    # Ensure a default '0' option is present
    if not form.id_marca_vehiculo.choices or form.id_marca_vehiculo.choices[0][0] != 0:
        form.id_marca_vehiculo.choices.insert(0, (0, 'Selecciona una marca de vehículo'))
    
    # --- IMPORTANT: Populate Dependent Select Choices on Server-Side for Validation ---
    
    # 3. Producto General (Dependent Selector: pieza_id)
    # Get the category ID from the product being edited
    # Use form.categoria_id.data because it will hold the pre-filled value from obj=producto
    selected_categoria_id = form.categoria_id.data 
    if selected_categoria_id and selected_categoria_id != 0:
        piezas_por_categoria = PiezaGenerica.query.filter_by(id_categoria=selected_categoria_id).order_by(PiezaGenerica.nombre).all()
        form.pieza_id.choices = [(p.id, p.nombre) for p in piezas_por_categoria]
    else:
        form.pieza_id.choices = [] # Ensure it's an empty list if no valid category selected
    # Always ensure the default option
    if not form.pieza_id.choices or form.pieza_id.choices[0][0] != 0:
        form.pieza_id.choices.insert(0, (0, 'Selecciona una pieza'))


    # 4. Modelo del Vehículo (Dependent Selector: id_modelo_vehiculo)
    # Get the vehicle brand ID from the product being edited
    # Use form.id_marca_vehiculo.data for the same reason
    selected_marca_vehiculo_id = form.id_marca_vehiculo.data 
    if selected_marca_vehiculo_id and selected_marca_vehiculo_id != 0:
        modelos_por_marca = Modelo.query.filter_by(id_marca=selected_marca_vehiculo_id).order_by(Modelo.nombre).all()
        form.id_modelo_vehiculo.choices = [(m.id, m.nombre) for m in modelos_por_marca]
    else:
        form.id_modelo_vehiculo.choices = [] # Ensure it's an empty list if no valid brand selected
    # Always ensure the default option
    if not form.id_modelo_vehiculo.choices or form.id_modelo_vehiculo.choices[0][0] != 0:
        form.id_modelo_vehiculo.choices.insert(0, (0, 'Selecciona un modelo'))


    if form.validate_on_submit():
        # Update product data from form
        try:
            # Check if values are '0' and convert to None if your model accepts nulls for non-selected
            # This is optional, depending on whether 0 is a valid ID or truly means 'none selected'
            if form.categoria_id.data == 0:
                producto.categoria_id = None
            else:
                producto.categoria_id = form.categoria_id.data

            if form.pieza_id.data == 0:
                producto.pieza_generica_id = None # Make sure this matches your model attribute
            else:
                producto.pieza_generica_id = form.pieza_id.data

            if form.id_marca_vehiculo.data == 0:
                producto.id_marca_vehiculo = None
            else:
                producto.id_marca_vehiculo = form.id_marca_vehiculo.data

            if form.id_modelo_vehiculo.data == 0:
                producto.id_modelo_vehiculo = None
            else:
                producto.id_modelo_vehiculo = form.id_modelo_vehiculo.data

            # Populate other fields normally (they don't need special handling if they can be 0 or empty string)
            
            producto.descripcion = form.descripcion.data
            producto.marca_repuesto = form.marca_repuesto.data
            producto.generacion = form.generacion.data
            producto.precio_compra = form.precio_compra.data
            producto.precio_venta = form.precio_venta.data
            producto.stock = form.stock.data
            producto.ubicacion = form.ubicacion.data
            
            db.session.commit()
            # --- Registrar la actividad de creación de producto ---
            log_activity(action="Producto editado", details=f"Producto: {form.descripcion.data}")
            
            flash('Producto actualizado exitosamente!', 'success')
            return redirect(url_for('listar_productos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el producto: {str(e)}', 'danger')
    
    # If it's a GET request or form submission failed, render the template
    return render_template('/productos/editar.html', form=form, producto=producto)

@app.route('/producto/eliminar/<int:id>', methods=['POST'])
def eliminar_producto(id):
    # ** This is correct way to acces a id from Object , when u want to use query_or_404
    # **Realiza una eliminacion logica (soft deletion) de un producto.En lugar de eliminar la fila, actualiza el campo 'is_active' a False.
    
    try:
        producto = Producto.query.filter_by(id=id).first_or_404()
        if producto:
            # Eliminar logicamente el producto
            producto.is_active=False
            db.session.commit()
            # --- Registrar la actividad de creación de producto ---
            log_activity(action="Producto eliminado", details=f"Producto: {form.descripcion.data}")
            flash('Producto eliminado exitosamente.', 'success')    
        else:
            flash("Producto no encontrado.", 'danger')
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar el producto: {str(e)}", 'danger')
    return redirect(url_for('listar_productos'))

### Rutas para Proveedores
@app.route('/proveedores/crear', methods=['GET', 'POST'])
@login_required
def crear_proveedor():
    form = ProveedorForm()
    if form.validate_on_submit():
        nuevo_proveedor = Proveedor(
            nombre=form.nombre.data,
            rif = form.rif.data,
            telefono=form.telefono.data,
            email=form.email.data
        )
        db.session.add(nuevo_proveedor)
        db.session.commit()
        # --- Registrar la actividad de creación de producto ---
        log_activity(action="Proveedor Creado", details=f"Proveedor: {form.nombre.data}")
        flash('Proveedor creado exitosamente.', 'success')
        return redirect(url_for('listar_proveedores')) # Asume que tendrás una ruta para listar proveedores
    return render_template('proveedores/crear.html', form=form)


@app.route('/proveedores')
@login_required
def listar_proveedores():
    proveedores = Proveedor.query.all()
    return render_template('proveedores/listar.html', proveedores=proveedores)

@app.route('/proveedores/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_proveedor(id):
    #** Object.query.filter_by(id=id) is the way to acces from id of a object
    proveedor = Proveedor.query.filter_by(id=id).first_or_404()
    form = ProveedorForm(obj=proveedor) #Carga los datos existentes en el formulario
    
    if form.validate_on_submit():
        form.populate_obj(proveedor)#Actualiza el objeto con los datos del formulario
        db.session.commit()
        flash('Proveedor actualizado exitosamente.', 'success')
        return redirect(url_for('listar_proveedores'))
    return render_template('proveedores/editar.html', form=form, proveedor=proveedor)

@app.route('/proveedores/eliminar/<int:id>', methods=['POST'])
def eliminar_proveedor(id):
    proveedor=Proveedor.query.filter_by(id=id).first_or_404()
    try:
        db.session.delete(proveedor)
        db.session.commit()
        flash('Proveedor eliminado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar el proveedor: {str(e)}", 'danger')
    return redirect(url_for('listar_proveedores'))

@app.route('/compras/crear', methods=['GET', 'POST'])
@login_required
def crear_compra():
    form = CompraForm()
    
    # --- DEBUG: Comprobación inicial de la solicitud ---
    print(f"\n--- INICIO DE CREAR_COMPRA ---")
    print(f"DEBUG: Método de la solicitud: {request.method}")
    if request.method == 'POST':
        print(f"DEBUG: Datos del formulario recibidos (request.form): {request.form}")
    # --- FIN DEBUG ---

    # Llenar las opciones del SelectField de proveedores
    proveedores = Proveedor.query.order_by(Proveedor.nombre).all()
    form.proveedor_id.choices = [(p.id, p.nombre) for p in proveedores]
    form.proveedor_id.choices.insert(0, (0, 'Selecciona un proveedor'))
    
    if not proveedores:
        flash('Debe crear al menos un proveedor antes de registrar una compra.', 'warning')
        print("DEBUG: No hay proveedores registrados. Redirigiendo a crear_proveedor.")
        return redirect(url_for('crear_proveedor'))
    
    productos_existentes = Producto.query.order_by(Producto.descripcion).all()
    if not productos_existentes:
        flash('Debes crear al menos un producto antes de registrar una compra.', 'warning')
        print("DEBUG: No hay productos registrados. Redirigiendo a crear_producto.")
        return redirect(url_for('crear_producto'))
    
    for i, detalle_form in enumerate(form.productos_comprados):
        pass # No hacemos nada aquí si producto_id es IntegerField/HiddenField
        
    print(f"DEBUG: Intentando validar el formulario con form.validate_on_submit()...")
    
    # --- Lógica para obtener y guardar/mostrar la tasa de cambio ---
    # Sugerencia: Extraer esta lógica a una función aparte para evitar duplicación.
    divisas_a_utilizar = ['USD','EUR']
    tasas_disponibles = {} #Aqui vamos a almacenar las tasas que vamos a utilizar
    
    for divisa in divisas_a_utilizar:
        # La función obtener_tasa_bcv() ahora devuelve una tupla.
        # Desempaquetamos la tupla y usamos solo el primer elemento.
        tasa_from_api = obtener_tasa_bcv(divisa)
        tasa_valor = tasa_from_api[0] if tasa_from_api and tasa_from_api[0] is not None else None
        print(f"DEBUG: Tasa de la API para {divisa}: {tasa_valor}")

        tasa_existente_hoy = TasaCambio.query.filter_by(
            moneda_origen = divisa,
            fecha = date.today()
        ).first()
        
        if tasa_valor and not tasa_existente_hoy:
            try: #Aqui guardamos dentro de la db UNA NUEVA Tasa de cambio
                nueva_tasa = TasaCambio(
                    moneda_origen = divisa,
                    tasa = tasa_valor,
                    fecha = date.today()
                )
                db.session.add(nueva_tasa)
                db.session.commit()
                print(f"DEBUG: Tasa de {divisa} a bs. ({tasa_valor}) guardada exitosamente para hoy.")
                flash(f"Tasa BCV {divisa} de Bs. ({tasa_valor}) actualizada para hoy.", 'info')
                tasas_disponibles[divisa] = tasa_valor
            except Exception as e:
                db.session.rollback()
                print(f"Error al guardar la tasa de cambio de {divisa}: {e}")
                flash(f"Error al guardar la tasa de cambio {divisa} de la API. Puede que ya exista o haya un problema de DB.")
        elif tasa_existente_hoy:
            tasa_valor = tasa_existente_hoy.tasa #Usar la de la DB en caso de que ya exista una registrada
            print(f"DEBUG: Usando tasa {divisa} de la DB para hoy: {tasa_valor}")
            tasas_disponibles[divisa] = tasa_valor
        else:
            flash(f"No se pudo obtener la tasa de cambio {divisa} a Bolivar. Por favor, asegúrese de que la API esté funcionando o ingrese la tasa manualmente.", 'danger')
            print(f"DEBUG: No se pudo obtener la tasa de {divisa}. La venta en {divisa} no será posible sin una tasa.")
            tasas_disponibles[divisa] = Decimal('0.0000') #Para que no falle al mostrar
    #Pre-llenar el campo de tasa_cambio_actual en el formulario para USD o la divisa predeterminada
    form.tasa_cambio_actual.data = tasas_disponibles.get('USD', Decimal('0.0000'))
    
    
    if form.validate_on_submit():
        print("DEBUG: form.validate_on_submit() es TRUE. Procediendo con el procesamiento de la compra.")
        print(f"DEBUG: Errores del formulario después de validate_on_submit() (debería estar vacío si TRUE): {form.errors}")
        moneda_seleccionada = form.moneda_compra.data
        tasa_cambio_para_compra = None
        
        # --- CAMBIO CRÍTICO: SEGURO DE QUE LA TASA ES DE HOY Y ES UN ÚNICO OBJETO ---
        tasa_db = TasaCambio.query.filter_by(moneda_origen=moneda_seleccionada, fecha=date.today()).first()
        if tasa_db:
            tasa_cambio_para_compra = tasa_db.tasa
        else:
            flash(f"No hay una tasa de cambio {moneda_seleccionada} a Bolivar disponible para hoy. Por favor, regístrela o intente actualizar.", 'danger')
            return render_template('compras/crear.html', form=form)
        
        # Asegurar que sea Decimal para cálculos precisos
        tasa_cambio_para_compra = Decimal(str(tasa_cambio_para_compra))
        
        total_compra_divisa = Decimal('0.00')
        productos_para_agregar = []
        
        productos_en_formulario = {}
        for item_form in form.productos_comprados.entries:
            producto_id = item_form.producto_id.data
            
            # --- Validaciones y Lógica de Stock ---
            producto = Producto.query.get(producto_id)
            
            if not producto:
                flash(f"El producto con ID {producto_id} no es valido.",'danger')
                return render_template('compras/crear.html', form=form)
            
            if producto_id in productos_en_formulario:
                flash('El producto ya fue agregado en esta compra. Si deseas más cantidad, edita el ítem existente.', 'danger')
                print(f"DEBUG: Producto duplicado detectado: {producto_id}. Redirigiendo.")
                return render_template('compras/crear.html', form=form)
            else:
                productos_en_formulario[producto_id] = True
        
        for item_form in form.productos_comprados.entries:
            producto = Producto.query.get(item_form.producto_id.data)
            marca_repuesto = item_form.marca_repuesto.data
            cantidad = item_form.cantidad.data
            precio_adquisicion = item_form.precio_adquisicion.data
            
            if not producto:
                flash('Uno de los productos seleccionados no es válido.', 'danger')
                print(f"DEBUG: Producto no válido encontrado: ID {item_form.producto_id.data}. Redirigiendo.")
                return render_template('compras/crear.html', form=form)
            
            precio_adquisicion_unitario_divisa = Decimal(str(producto.precio_compra))
            
            # Subtotal en la moneda de adquisición
            subtotal_item_divisa = cantidad * precio_adquisicion_unitario_divisa
            total_compra_divisa += subtotal_item_divisa
            print(f"subtotal en divisas {subtotal_item_divisa} \n total en divisas {total_compra_divisa}")
            
            
            productos_para_agregar.append({
                'producto': producto,
                'marca_repuesto': marca_repuesto,
                'cantidad': cantidad,
                'precio_adquisicion': precio_adquisicion_unitario_divisa #Guardar el precio de compra en divisas
            })
            print(f"DEBUG: Producto {producto.descripcion} añadido a lista para agregar.")
        #---Calculo del total en bolivar---
        total_compra_bs = (total_compra_divisa * tasa_cambio_para_compra).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Crear la instancia de compra con los campos nuevos
        nueva_compra = Compra(
            numero_factura=form.numero_factura.data,
            proveedor_id=form.proveedor_id.data,
            total_compra_divisa=total_compra_divisa,
            moneda_total_divisa=moneda_seleccionada,
            tasa_cambio_aplicada=tasa_cambio_para_compra,
            total_compra_bs=total_compra_bs
        )
        db.session.add(nueva_compra)
        db.session.flush() 
        print(f"DEBUG: Nueva compra creada con ID: {nueva_compra.id}")
        
        for item_data in productos_para_agregar:
            detalle = DetalleCompra(
                compra_id=nueva_compra.id,
                producto_id=item_data['producto'].id,
                marca_repuesto=item_data['marca_repuesto'],
                cantidad=item_data['cantidad'],
                precio_adquisicion=item_data['precio_adquisicion']
            )
            db.session.add(detalle)
            print(f"DEBUG: Detalle de compra añadido para Producto ID: {item_data['producto'].id}")
            
            item_data['producto'].stock += item_data['cantidad']
            db.session.add(item_data['producto']) 
            print(f"DEBUG: Stock actualizado para Producto ID: {item_data['producto'].id}, Nuevo stock: {item_data['producto'].stock}")
            
        db.session.commit()
        # --- Registrar la actividad de creación de producto ---
        log_activity(action="Compra registrada", details=f"N°FACTURA: {form.numero_factura.data}")
        flash('Compra registrada exitosamente y stock actualizado.', 'success')
        print("DEBUG: Compra y stock actualizados. Redirigiendo a listar_compras.")
        return redirect(url_for('listar_compras'))
    else:
        print("DEBUG: form.validate_on_submit() es FALSE. El formulario NO ES VÁLIDO.")
        print(f"DEBUG: Errores de validación del formulario: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en {field}: {error}", 'danger')
                print(f"DEBUG: Flash error: Campo '{field}', Mensaje: '{error}'")
    print(f"Valor de la tasa EUR {tasas_disponibles.get('EUR',Decimal('0.0000'))}")
    return render_template('compras/crear.html', form=form,
                                                    usd_rate=tasas_disponibles.get('USD', Decimal('0.0000')),
                                                    eur_rate=tasas_disponibles.get('EUR', Decimal('0.0000')))


@app.route('/compras')
@login_required
def listar_compras():
    compras = Compra.query.order_by(Compra.fecha_compra.desc()).all()
    return render_template('compras/listar.html', compras=compras)

@app.route('/compras/<int:compra_id>')
def ver_detalle_compra(compra_id):
    compra=Compra.query.filter_by(id=compra_id).first_or_404()
    return render_template('compras/detalle.html', compra=compra)

@app.route('/compras/imprimir_codigos/<int:compra_id>')
def imprimir_codigos_productos(compra_id):
    """
    Muestra una página con códigos de barras listos para imprimir.
    Obtiene los productos de una compra específica.
    """
    # 1. Obtener la compra (esto ya lo tenías)
    compra = Compra.query.filter_by(id=compra_id).first_or_404()
    
    # 2. Obtener los detalles de esa compra (los productos y cantidades)
    detalles_compra = DetalleCompra.query.filter_by(compra_id=compra.id).all()
    
    # 3. Preparar una lista en el formato que la plantilla necesita
    # ¡IMPORTANTE! Agrega el objeto completo del producto, no solo las propiedades.
    productos_para_imprimir = []
    for detalle in detalles_compra:
        productos_para_imprimir.append({
            'descripcion': detalle.detalle_compras.descripcion, # El objeto del producto
            'producto_id': detalle.producto_id,
            'cantidad': detalle.cantidad,
            'precio_venta': detalle.detalle_compras.precio_venta
        })
    
    # 4. Renderizar la plantilla, pasando la lista de productos y la función
    return render_template(
        'compras/imprimir_codigos.html', 
        productos=productos_para_imprimir,
        generar_codigo_barras_base64=generar_codigo_barras_base64
    )

### Rutas para compras
"""
Inicialización del Formulario y Opciones:

form = CompraForm(): Crea una instancia del formulario.

form.proveedor_id.choices = ...: Aquí es crucial. Llenamos las opciones del SelectField de proveedor con datos de la base de datos. (p.id, p.nombre) es el formato (valor, etiqueta).

for detalle_form in form.productos_comprados:: Como productos_comprados es un FieldList de DetalleCompraForm, necesitamos iterar sobre cada sub-formulario y también llenar sus producto_id.choices.

Manejo de "sin proveedores/productos": Se añaden flash messages y redirecciones si no hay proveedores o productos para evitar errores.

if form.validate_on_submit():: Esto se ejecuta cuando el formulario se envía (POST) y pasa todas las validaciones de WTForms.

Validación de Duplicados y Cantidad: Se agrega una validación manual para evitar agregar el mismo producto dos veces en una compra y asegurar que la cantidad sea positiva.

total_compra = 0: Inicializa una variable para sumar el total de la compra.

Recorrido de productos_comprados: Iteramos sobre cada DetalleCompraForm (cada producto añadido a la compra).

producto = Producto.query.get(item_form.producto_id.data): Recupera el objeto Producto real de la base de datos usando el ID seleccionado.

Calculamos el total_compra.

Guardamos los datos de cada ítem en una lista productos_para_agregar para procesarlos después de crear la Compra principal.

Crear Compra:

nueva_compra = Compra(...): Crea la instancia de la compra.

db.session.add(nueva_compra): La añade a la sesión.

db.session.flush(): ¡Importante! flush() le dice a SQLAlchemy que envíe los cambios pendientes a la base de datos pero sin hacer un commit definitivo todavía. Esto es para que nueva_compra.id (el ID de la compra recién creada) esté disponible para ser usado en los DetalleCompra que se crearán a continuación. Sin flush(), nueva_compra.id sería None.

Crear DetalleCompra y Actualizar Stock:

Iteramos sobre productos_para_agregar.

detalle = DetalleCompra(...): Creamos cada detalle de compra, enlazándolo con nueva_compra.id.

db.session.add(detalle): Añade el detalle a la sesión.

item_data['producto'].stock += item_data['cantidad']: ¡Esto es clave! Actualiza el stock del Producto directamente en la instancia que recuperamos.

db.session.add(item_data['producto']): Esto le indica a SQLAlchemy que este objeto Producto ha sido modificado y necesita ser actualizado en la base de datos.

db.session.commit(): Finalmente, se guardan todos los cambios (la nueva Compra, todos los DetalleCompra y las actualizaciones de stock de los Productos) de forma transaccional. Si algo falla antes del commit, todo se revierte.

Mensaje Flash y Redirección: Informa al usuario y lo lleva a la lista de compras
"""
# ... Más rutas para editar, eliminar productos, gestionar compras, ventas, clientes, etc.

### Rutas para Clientes
@app.route('/clientes/crear', methods=['GET', 'POST'])
@login_required
def crear_cliente():
    form=ClienteForm()
    if form.validate_on_submit():
        nuevo_cliente = Cliente(
            nombre=form.nombre.data,
            apellido=form.apellido.data,
            cedula_rif=form.cedula_rif.data,
            direccion=form.direccion.data,
            telefono=form.telefono.data,
            email=form.email.data
        )
        db.session.add(nuevo_cliente)
        db.session.commit()
        # --- Registrar la actividad de creación de producto ---
        log_activity(action="Cliente creado", details=f"Producto: {form.cedula_rif.data}")
        flash('Cliente creado Exitosamente.' 'success')#Se asume que habra una ruta para listar los clientes
        return redirect(url_for('listar_clientes'))
    return render_template('clientes/crear.html', form=form)

@app.route('/clientes')
@login_required
def listar_clientes():
    clientes = Cliente.query.all()
    return render_template('clientes/listar.html', clientes=clientes)

@app.route('/clientes/editar/<int:id>', methods=['GET','POST'])
def editar_cliente(id):
    cliente = Cliente.query.filter_by(id=id).first_or_404()
    form = ClienteForm(obj=cliente) #Carga los datos existentes en el formulario
    
    if form.validate_on_submit():
        form.populate_obj(cliente)#Actualiza el objeto con los datos del formulario
        db.session.commit()
        log_activity(action="Cliente Editado", details=f"Producto: {form.cedula_rif.data}")
        flash('Cliente actualizado exitosamente.', 'success')
        return redirect(url_for('listar_clientes'))
    return render_template('clientes/editar.html', form=form, cliente=cliente)


@app.route('/clientes/eliminar/<int:id>', methods=['GET'])
def eliminar_cliente(id):
    cliente = Cliente.query.filter_by(id=id).first_or_404()
    try:
        db.session.delete(cliente)
        db.session.commit()
        log_activity(action="Cliente eliminado", details=f"Producto: {form.cedula_rif.data}")
        flash('Cliente eliminado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar el cliente: {str(e)}", 'danger')
    return redirect(url_for('listar_clientes'))


# La función para obtener la tasa del BCV, ahora corregida para siempre devolver una tupla.
def obtener_tasa_bcv(moneda_origen):
    """
    Obtiene la tasa de cambio oficial (compra y venta) para una moneda específica (USD o EUR)
    usando la API de DolarAPI.com.

    Args:
        moneda_origen (str): La moneda de la cual obtener la tasa ('USD' o 'EUR').

    Returns:
        tuple: Una tupla con (precio_compra, precio_venta, fecha_actualizacion),
               o (None, None, None) si hay un error.
    """
    try:
        if moneda_origen == 'USD':
            url = "https://ve.dolarapi.com/v1/dolares/oficial"
        
        else:
            print(f"ADVERTENCIA: Moneda {moneda_origen} no soportada por la API")
            return None, None, None
        
        response = requests.get(url, timeout=5)
        
        response.raise_for_status() #Lanza una excepcion para errores HTTP como 404 p 503
        
        data = response.json()
        
        #Accedemos al promedio que es el que trae el precio de la divisa y fecha que trae la fecha de la ultima actualizacion, que estan en el JSON de la API 
        tasa_bcv = data.get('promedio')
        fecha = data.get('fechaActualizacion', 'N/A')
        
        if tasa_bcv is not None:
            print(f"valores traidos de la api promedio: {tasa_bcv} - fecha de la tasa: {fecha}")
            #Convertimos a Decimal para tener la mayor precision en los montos
            return Decimal(str(tasa_bcv)), fecha
        else:
            print(f"Error de conexion al obtener tasa de {moneda_origen}: {req_err}")
            return None, None, None
    
    except requests.exceptions.RequestException as req_err:
        print(f"Error de conexion al obtener tasa de {moneda_origen}: {req_err}")
    except (json.JSONDecodeError, KeyError) as parse_err:
        print(f"Error al parsear la respuesta JSON o llave no encontrada oara {moneda_origen}: {parse_err}. Respuesta: {response.text}")
    except Exception as e:
        print(f"Error inesperado al obtener la tasa de {moneda_origen}: {e}")
    
    #En caso de cualquier error, se retorna una tupla de tres elementos
    return None, None, None

@app.route('/ventas/crear', methods=['GET','POST'])
def crear_venta():
    form = VentaForm()

    # LLenar las opciones del SelectField para clientes
    form.cliente_id.choices = [(c.id, f"{c.nombre} {c.apellido}.({c.cedula_rif})") for c in Cliente.query.order_by(Cliente.nombre).all()]
    if not form.cliente_id.choices:
        flash('Debes crear al menos un cliente antes de poder registrar una venta', 'warning')
        return redirect(url_for('crear_cliente'))

    # Llenar las opciones del SelectField para productos
    productos_existentes = Producto.query.order_by(Producto.descripcion).all()
    if not productos_existentes:
        flash('Debes crear al menos un producto antes de registrar una venta.', 'warning')
        return redirect(url_for('crear_producto'))
    
    for detalle_form in form.productos_vendidos:
        detalle_form.producto_id.choices = [(p.id, p.descripcion) for p in productos_existentes]

    # --- Lógica para obtener y guardar/mostrar la tasa de cambio ---
    divisas_a_utilizar = ['USD','EUR']
    tasas_disponibles = {} #Aqui vamos a almacenar las tasas que podemos usar o mostrar
    
    for divisa in divisas_a_utilizar:
        tasa_actual_api = obtener_tasa_bcv(divisa)
        tasa_existente_hoy = TasaCambio.query.filter_by(
            moneda_origen = divisa,
            fecha= date.today()
        ).first()
        
        if tasa_actual_api and not tasa_existente_hoy:
            try: #Aqui guardamos dentro de la DB una nueva TASA DE CAMBIO
                nueva_tasa = TasaCambio(
                    moneda_origen = divisa,
                    tasa = tasa_actual_api,
                    fecha =  date.today()
                )
                db.session.add(nueva_tasa)
                db.session.commit()
                print(f"Tasa de {divisa} a Bs. ({tasa_actual_api}) guardada exitosamente para hoy.")
                flash(f"Tasa BCV {divisa} a Bs. ({tasa_actual_api}) actualizada para hoy.", 'info')
                tasas_disponibles[divisa] = tasa_actual_api
            except Exception as e:
                db.session.rollback()
                print(f"Error al guardar la tasa de cambio de {divisa}: {e}")
                flash(f'Error al guardar la tasa de cambio {divisa} de la API. Puede que ya exista o haya un problema de DB.', 'warning')
        elif tasa_existente_hoy:
            tasa_actual_api = tasa_existente_hoy.tasa # Usar la de la DB si ya existe
            print(f"Usando tasa {divisa} de la DB para hoy: {tasa_actual_api}")
            tasas_disponibles[divisa] = tasa_actual_api
        else:
            flash(f'No se pudo obtener la tasa de cambio {divisa} a Bolívar. Por favor, asegúrese de que la API esté funcionando o ingrese la tasa manualmente.', 'danger')
            print(f"No se pudo obtener la tasa de {divisa}. La venta en {divisa} no será posible sin una tasa.")
            tasas_disponibles[divisa] = Decimal('0.0000') # Para que no falle al mostrar
    
    #Pre-llenar el campo de tasa_cambio_actual en el formulario para USD o la divisa que se considere principal
    form.tasa_cambio_actual.data = tasas_disponibles.get('USD', Decimal('0.0000'))

    # Si la solicitud es POST y el formulario es válido
    if form.validate_on_submit():
        print("Formulario válido, procesando venta...")
        
        moneda_seleccionada = form.moneda_venta.data
        tasa_cambio_para_venta = None

        tasa_db = TasaCambio.query.filter_by(moneda_origen=moneda_seleccionada, fecha=date.today()).first()

        if tasa_db:
            tasa_cambio_para_venta = tasa_db.tasa
        else:
            flash(f'No hay una tasa de cambio {moneda_seleccionada} a Bolívar disponible para hoy.', 'danger')
            return render_template('ventas/crear.html', form=form)
        
        tasa_cambio_para_venta = Decimal(str(tasa_cambio_para_venta)) 
        
        total_venta_divisa = Decimal('0.00')
        productos_en_formulario = {} 
        detalles_para_db = [] # Nueva lista para almacenar los objetos DetalleVenta

        # --- Bucle Consolidado de Validación, Cálculo y Preparación ---
        for item_form in form.productos_vendidos.entries:
            producto_id = item_form.producto_id.data
            cantidad_solicitada = Decimal(str(item_form.cantidad.data))
            
            producto = Producto.query.get(producto_id)
            
            if not producto:
                flash(f"El producto con ID {producto_id} no es válido.", 'danger')
                return render_template('ventas/crear.html', form=form)
            
            if cantidad_solicitada <= 0:
                flash(f"La cantidad para '{producto.descripcion}' debe ser un número positivo.", 'danger')
                return render_template('ventas/crear.html', form=form)

            if producto_id in productos_en_formulario:
                flash(f"El producto '{producto.descripcion}' está duplicado en los detalles de la venta.", 'danger')
                return render_template('ventas/crear.html', form=form)
            else:
                productos_en_formulario[producto_id] = True

            if producto.stock < cantidad_solicitada:
                flash(f"Stock insuficiente para '{producto.descripcion}'. Disponible: {producto.stock}, Solicitado: {cantidad_solicitada}.", 'danger')
                return render_template('ventas/crear.html', form=form)

            # Calculamos el subtotal del item en la divisa
            precio_unitario_producto_divisa = Decimal(str(producto.precio_venta))
            subtotal_item_divisa = cantidad_solicitada * precio_unitario_producto_divisa
            total_venta_divisa += subtotal_item_divisa
            
            # Preparamos el objeto DetalleVenta y actualizamos el stock del producto
            detalle = DetalleVenta(
                producto_id=producto.id,
                cantidad=cantidad_solicitada,
                precio_venta_unitario=precio_unitario_producto_divisa 
            )
            detalles_para_db.append(detalle)
            producto.stock -= cantidad_solicitada
            db.session.add(producto) # Agregamos el producto modificado a la sesión

        # --- Lógica de Creación y Guardado (Fuera del Bucle) ---
        total_venta_bs = (total_venta_divisa * tasa_cambio_para_venta).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        numero_nota_entrega = f"NE-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        nueva_venta = Venta(
            id_cliente=form.cliente_id.data,
            total_venta_divisa=total_venta_divisa,
            moneda_total_divisa=moneda_seleccionada,
            tasa_cambio_aplicada=tasa_cambio_para_venta, 
            total_venta_bs=total_venta_bs, 
            numero_nota_entrega=numero_nota_entrega,
            detalles=detalles_para_db # Asignamos la lista de detalles completa
        )
        
        db.session.add(nueva_venta)
        
        try:
            db.session.commit()
            log_activity(action="Venta creada", details=f"Producto: {form.cliente_id.data}")
            flash(f"Venta registrada exitosamente. Nota de Entrega N°: {numero_nota_entrega}. Total: {total_venta_bs} Bs.", 'success')
            return redirect(url_for('listar_ventas'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al registrar la venta: {str(e)}", 'danger')
            print(f"Error de base de datos: {str(e)}")
            return render_template('ventas/crear.html', form=form)
        print(f"Valor de la tasa EUR {tasas_disponibles.get('EUR',Decimal('0.0000'))}")
            
    # Si el formulario no es válido o es GET
    print("Formulario no válido o solicitud GET. Errores:", form.errors)
    return render_template('ventas/crear.html', 
                        form=form,
                        usd_rate=tasas_disponibles.get('USD', Decimal('0.0000')),
                        eur_rate=tasas_disponibles.get('EUR', Decimal('0.0000')))

@app.route('/ventas')
@login_required
def listar_ventas():
    ventas = Venta.query.order_by(Venta.fecha_venta.desc()).all()
    return render_template('ventas/listar.html', ventas=ventas)

@app.route('/ventas/<int:venta_id>')
def ver_detalle_venta(venta_id):
    venta= Venta.query.filter_by(id=venta_id).first_or_404()
    return render_template('ventas/detalle.html', venta=venta)

