from app import db # Importa la instancia de SQLAlchemy desde tu app.py
import datetime
from datetime import *
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash 

# --- Modelo de roles para la gestión de permisos ---
class Role(db.Model):
    """
    Modelo de base de datos para los roles de usuario (ej. 'admin', 'user').
    Permite asignar permisos y funcionalidades específicas.
    """
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True)
    # Relación con el modelo User
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>'

# --- Modelo de usuario unificado para autenticación y logs ---
class User(UserMixin, db.Model):
    """
    Modelo de base de datos para los usuarios del sistema.
    Hereda de UserMixin para la autenticación y contiene campos
    para el registro de actividad.
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # Relación con la tabla Role (para roles/permisos)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    
    # Relación con la tabla ActivityLog (para el registro de actividad)
    logs = db.relationship('ActivityLog', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        """
        Hashea la contraseña para un almacenamiento seguro.
        """
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """
        Comprueba si la contraseña proporcionada coincide con el hash almacenado.
        """
        return check_password_hash(self.password_hash, password)

# --- Modelo para el registro de actividad del usuario ---
class ActivityLog(db.Model):
    """
    Modelo de base de datos para registrar las acciones de los usuarios.
    """
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<ActivityLog {self.user.username} - {self.action} at {self.timestamp}>"

class Marca(db.Model):
    __tablename__ = 'marcas' # Nombre de tabla en plural
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    
    modelos = db.relationship('Modelo', backref='marca', lazy=True)

    def __repr__(self):
        return f"<Marca {self.nombre}>"

class Modelo(db.Model):
    __tablename__ = 'modelos' # Nombre de tabla en plural
    id = db.Column(db.Integer, primary_key=True)
    id_marca = db.Column(db.Integer, db.ForeignKey('marcas.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Modelo {self.nombre} (Marca: {self.marca.nombre})>" # Corrección: self.marca.nombre

class Categoria(db.Model):
    __tablename__ = 'categorias' # **CAMBIADO a plural**
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)

    # **CAMBIADO**: 'piezas_genericas' para reflejar el modelo PiezaGenerica
    piezas_genericas = db.relationship('PiezaGenerica', backref='categoria_pieza', lazy=True) 

    def __repr__(self):
        return f"<Categoria {self.nombre}>"
    
class PiezaGenerica(db.Model): # **CAMBIADO: Nombre del modelo a PiezaGenerica**
    __tablename__ = 'piezas_genericas' # **CAMBIADO a plural**
    id = db.Column(db.Integer, primary_key=True)
    # FK a la nueva tabla 'categorias' (asumiendo que Categoria se llama 'categorias')
    id_categoria = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False) 
    nombre = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        # **CAMBIADO**: Acceso a la relación a través de 'categoria_pieza' (backref)
        return f"<PiezaGenerica {self.nombre} (Categoría: {self.categoria_pieza.nombre})>"


class Producto(db.Model):
    __tablename__ = 'productos' # Nombre de tabla en plural
    id = db.Column(db.Integer, primary_key=True)
    
    descripcion = db.Column(db.String(255), nullable=False)
    marca_repuesto = db.Column(db.String(50), nullable=False)

    # --- CAMPOS Y RELACIONES PARA CATEGORIA Y PIEZA GENERAL ---
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False) # **FK a 'categorias'**
    pieza_generica_id = db.Column(db.Integer, db.ForeignKey('piezas_genericas.id'), nullable=False) # **CAMBIADO a pieza_generica_id y FK a 'piezas_genericas'**
    
    # Relaciones para acceder a los objetos Categoria y PiezaGenerica
    # **CAMBIADO: nombres de relaciones a singular y backrefs únicos**
    categoria_rel = db.relationship('Categoria', backref='productos_por_categoria', lazy=True)
    pieza_generica_rel = db.relationship('PiezaGenerica', backref='productos_por_pieza_generica', lazy=True)
    # --- FIN NUEVOS CAMPOS Y RELACIONES ---

    # --- CAMPOS EXISTENTES PARA RELACIÓN CON VEHÍCULO ---
    id_marca_vehiculo = db.Column(db.Integer, db.ForeignKey('marcas.id'), nullable=False)
    id_modelo_vehiculo = db.Column(db.Integer, db.ForeignKey('modelos.id'), nullable=False)
    
    # Relaciones para acceder a los objetos Marca y Modelo de Vehículo
    marca_vehiculo = db.relationship('Marca', foreign_keys=[id_marca_vehiculo], backref='productos_por_marca_vehiculo', lazy=True)
    modelo_vehiculo = db.relationship('Modelo', foreign_keys=[id_modelo_vehiculo], backref='productos_por_modelo_vehiculo', lazy=True)
    # --- FIN CAMPOS EXISTENTES ---

    generacion = db.Column(db.String(50))
    precio_compra = db.Column(db.Numeric(10, 2), nullable=False)
    precio_venta = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    ubicacion = db.Column(db.String(100))
    codigo_barras_base64 = db.Column(db.String(500), unique=True)
    fecha_registro = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_active=db.Column(db.Boolean, default=True, nullable=False)
    # Relaciones con DetalleCompra y DetalleVenta
    # AÑADIDO: overlaps="detalle_producto_compra" para resolver el warning
    compras_detalle = db.relationship('DetalleCompra', backref='producto_compra', lazy=True)
    # AÑADIDO: overlaps="detalle_producto_venta" para resolver el warning
    ventas_detalle = db.relationship('DetalleVenta', backref='producto_venta', lazy=True)#overlaps = funciona para 

    def __repr__(self):
        return f"<Producto {self.descripcion} - Stock: {self.stock}>"


class Proveedor(db.Model):
    __tablename__ = 'proveedores' # Nombre de tabla en plural
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    rif = db.Column(db.String(50), nullable=False, unique=True)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120))

    compras = db.relationship('Compra', backref='proveedor', lazy=True)

    def __repr__(self):
        return f"<Proveedor {self.nombre}>"

class Compra(db.Model):
    __tablename__ = 'compras' # Nombre de tabla en plural
    fecha_compra = db.Column(db.DateTime, default=db.func.current_timestamp())
    id = db.Column(db.Integer, primary_key=True)
    numero_factura = db.Column(db.String(80), nullable=True)
    # Asumiendo que proveedor_id es el nombre de la columna en la tabla `compras`
    # que es una FK a `proveedores.id`
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'), nullable=False) 
    total_compra_divisa = db.Column(db.Numeric(10, 2), nullable=False)
    moneda_total_divisa = db.Column(db.String(3), nullable=False)    # Nuevo: 'USD' o 'EUR'
    tasa_cambio_aplicada = db.Column(db.Numeric(10, 4), nullable=False) # Nuevo: Tasa BCV usada para esta venta
    total_compra_bs = db.Column(db.Numeric(10, 2), nullable=False)
    detalles = db.relationship('DetalleCompra', backref='compra', lazy=True)

    def __repr__(self):
        return f"<Compra {self.id} - Fecha: {self.fecha_compra}>"

class DetalleCompra(db.Model):
    __tablename__ = 'detalle_compras' # **CAMBIADO a plural**
    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('compras.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    marca_repuesto = db.Column(db.String(50), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_adquisicion = db.Column(db.Numeric(10, 2), nullable=False)
    
    # --- Relacion con el producto ---
    # AÑADIDO: overlaps="producto_compra" para resolver el warning
    detalle_compras = db.relationship('Producto', viewonly=True, lazy=True, overlaps="producto_compra")

    def __repr__(self):
        return f"<DetalleCompra Compra:{self.compra_id} Producto:{self.producto_id} Cantidad:{self.cantidad}>"


class Cliente(db.Model):
    __tablename__ = 'clientes' # Nombre de tabla en plural
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    cedula_rif = db.Column(db.String(20), unique=True, nullable=False)
    direccion = db.Column(db.Text)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120))

    ventas = db.relationship('Venta', backref='cliente', lazy=True)

    def __repr__(self):
        return f"<Cliente {self.nombre} {self.apellido}>"

class Venta(db.Model):
    __tablename__ = 'ventas' # Nombre de tabla en plural
    id = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    fecha_venta = db.Column(db.DateTime, default=db.func.current_timestamp())
    numero_nota_entrega = db.Column(db.String(50), unique=True, nullable=False)
    total_venta_divisa = db.Column(db.Numeric(10, 2), nullable=False) # Nuevo: Total en la moneda original (USD/EUR)
    moneda_total_divisa = db.Column(db.String(3), nullable=False)    # Nuevo: 'USD' o 'EUR'
    tasa_cambio_aplicada = db.Column(db.Numeric(10, 4), nullable=False) # Nuevo: Tasa BCV usada para esta venta
    total_venta_bs = db.Column(db.Numeric(10, 2), nullable=False)      # Nuevo: Total en Bolívar Soberano (Bs.)
    detalles = db.relationship('DetalleVenta', backref='venta', lazy=True)

    def __repr__(self):
        return f"<Venta {self.id} - Nota de Entrega: {self.numero_nota_entrega}>"

class DetalleVenta(db.Model):
    __tablename__ = 'detalle_ventas' # **CAMBIADO a plural**
    id = db.Column(db.Integer, primary_key=True)
    id_venta = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_venta_unitario = db.Column(db.Numeric(10, 2), nullable=False)

    # AÑADIDO: overlaps="producto_venta" para resolver el warning
    detalle_ventas = db.relationship('Producto', viewonly=True, lazy=True, overlaps="producto_venta")

    def __repr__(self):
        return f"<DetalleVenta Venta:{self.id_venta} Producto:{self.producto_id} Cantidad:{self.cantidad}>"
    
class TasaCambio(db.Model):
    __tablename__ = 'tasas_cambio'
    id = db.Column(db.Integer, primary_key=True)
    moneda_origen = db.Column(db.String(3), nullable=False) # Ej: 'USD', 'EUR'
    moneda_destino = db.Column(db.String(3), default='VES', nullable=False) # Bolívar Soberano
    tasa = db.Column(db.Numeric(10, 4), nullable=False) # 10 dígitos en total, 4 decimales
    fecha = db.Column(db.Date, default=date.today, nullable=False) # Una tasa por día y moneda_origen

    # Añadir un índice único compuesto si necesitas más de una moneda_origen por día
    __table_args__ = (
        db.UniqueConstraint('moneda_origen', 'fecha', name='_moneda_fecha_uc'),
    )

    def __repr__(self):
        return f"<TasaCambio {self.moneda_origen} a {self.moneda_destino}: {self.tasa} en {self.fecha}>"
