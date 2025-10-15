 # Definición de formularios WTForms
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, FormField,FieldList, IntegerField, SelectField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Length, Optional, EqualTo, Email, ValidationError

# --- Formularios para Registro de usuario --- #
class RegistrationForm(FlaskForm):
    """
    Formulario para el registro de nuevos usuarios.
    """
    username = StringField('Nombre de usuario', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar contraseña', validators=[DataRequired(), EqualTo('password', message='Las contraseñas deben coincidir')])
    submit = SubmitField('Registrarse')
    
    # Validaciones personalizadas para evitar usuarios y correos duplicados
    def validate_username(self, username):
        from models import User # Importación local
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ese nombre de usuario ya está en uso. Por favor, elige uno diferente.')

    def validate_email(self, email):
        from models import User # Importación local
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Ese correo electrónico ya está en uso. Por favor, elige uno diferente.')

# --- Formularios para Login --- #
class LoginForm(FlaskForm):
    """Formulario para el login de usuario."""
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')


# --- Formulario para la creacion de un producto --- #
class ProductoForm(FlaskForm):
    categoria_id = SelectField('Categoría de la Pieza', coerce=int, validators=[DataRequired(message="Seleccione una categoría.")])
    pieza_id = SelectField('Producto General (Tipo de Pieza)', coerce=int, validators=[DataRequired(message="Seleccione un tipo de pieza.")])
    descripcion = TextAreaField('Descripción', validators=[DataRequired(), Length(min=5, max=200)])
    marca_repuesto = StringField('Marca del Repuesto', validators=[DataRequired(), Length(max=100)])
    id_marca_vehiculo = SelectField('Marca del Vehículo', coerce=int, validators=[Optional()])
    id_modelo_vehiculo = SelectField('Modelo del Vehículo', coerce=int, validators=[Optional()])
    generacion = StringField('Generación (Ej: 2000-2005)', validators=[Optional(), Length(max=50)])
    precio_compra = DecimalField('Precio de Compra', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    precio_venta = DecimalField('Precio de Venta', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    stock = IntegerField('Stock Inicial', validators=[DataRequired(), NumberRange(min=0)])
    ubicacion = StringField('Ubicación', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Guardar Cambios')

    def __init__(self, *args, **kwargs):
        super(ProductoForm, self).__init__(*args, **kwargs)
        from models import Categoria, Marca # Mover la importación aquí
        
        self.categoria_id.choices = [(c.id, c.nombre) for c in Categoria.query.order_by('nombre').all()]
        self.categoria_id.choices.insert(0, (0, 'Selecciona una categoría'))

        self.id_marca_vehiculo.choices = [(m.id, m.nombre) for m in Marca.query.order_by('nombre').all()]
        self.id_marca_vehiculo.choices.insert(0, (0, 'Selecciona una marca de vehículo'))
        
        if not self.pieza_id.choices: 
            self.pieza_id.choices = [(0, 'Selecciona una pieza')]
        if not self.id_modelo_vehiculo.choices: 
            self.id_modelo_vehiculo.choices = [(0, 'Selecciona un modelo')]


# --- Sub-formulario para cada detalle de producto en la compra ---
class DetalleCompraForm(FlaskForm):
    # producto_id es el ID del producto existente en la base de datos
    
    producto_id = IntegerField('ID Producto', validators=[DataRequired()])
    
    # Es crucial que este campo exista para capturar la marca_repuesto
    # que se envía como hidden input desde el frontend.
    marca_repuesto = StringField('Marca Repuesto', validators=[DataRequired(), Length(max=100)])
    
    cantidad = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1, message="La cantidad debe ser al menos 1.")])
    precio_adquisicion = DecimalField('Precio Adquisición', validators=[DataRequired(), NumberRange(min=0.01, message="El precio de adquisición debe ser mayor a 0.")])
    
    
    delete_item = SubmitField('Eliminar')
    
# --- Formulario principal de Compra ---
class CompraForm(FlaskForm):
    # proveedor_id es un SelectField porque se selecciona de una lista de proveedores existentes
    # Las opciones se llenarán dinámicamente en la ruta
    proveedor_id = SelectField('Proveedor', coerce=int, validators=[DataRequired(message="Por favor, selecciona un proveedor.")])
    numero_factura = StringField('Numero de Factura', validators=[Optional(), Length(max=100)])
    #Nuevo campo para seleccionar la moneda de la venta
    moneda_compra = SelectField("Moneda de Compra", choices=[('USD','USD - Dolar'),('EUR','EUR - Euro')], validators=[DataRequired()])
    # Campo para mostrar la tasa de cambio actual (solo lectura, se llenará en JS o Python)
    # Podría ser un HiddenField o un StringField read-only si quieres mostrarlo
    tasa_cambio_actual = DecimalField('Tasa de Cambio BCV (Bs. por 1 USD/EUR)', render_kw={'readonly':False}, places=4)
    # FieldList para manejar múltiples instancias de DetalleCompraForm
    # min_entries=1 asegura que al menos un producto sea añadido para la compra
    productos_comprados = FieldList(FormField(DetalleCompraForm), min_entries=1)
    
    submit = SubmitField('Registrar Compra')
    
# --- Formulario para crear un nuevo proveedor (Si no existe)---
class ProveedorForm(FlaskForm):
    nombre = StringField('Nombre Proveedor', validators = [DataRequired()])
    rif = StringField('Rif', validators = [DataRequired(), Length(min=7, max=9)])
    telefono = StringField('Telefono', validators=[DataRequired(),Length(min=11, max=11)])
    email = StringField('Email')
    submit = SubmitField('Guardar')
    
"""
Explicación detallada:

DetalleCompraForm: Este no es un formulario que el usuario llenará directamente, sino un "sub-formulario" que representa una línea de un producto específico dentro de una compra.

producto_id: Usaremos un SelectField para que el usuario elija de una lista de productos ya existentes. coerce=int es crucial para asegurar que el valor recibido sea un entero (el ID del producto).

cantidad: La cantidad de ese producto comprado.

precio_adquisicion: El precio unitario al que se compró ese producto específico en esta transacción.

CompraForm: Este es el formulario principal para la compra.

proveedor_id: Similar a producto_id, para elegir un proveedor existente.

FieldList(FormField(DetalleCompraForm), min_entries=1): Esta es la clave para añadir múltiples productos.

FieldList permite tener una lista de campos.

FormField(DetalleCompraForm) dice que cada elemento en esa lista será una instancia de DetalleCompraForm.

min_entries=1 asegura que, por defecto, el formulario mostrará al menos una sección para añadir un producto. Si necesitas que el usuario pueda añadir más dinámicamente, eso requerirá JavaScript en el frontend para duplicar esas secciones del formulario.
"""

#--- Sub-Formulario para cada item de producto en la venta ---
class DetalleVentaForm(FlaskForm):
    producto_id = SelectField('Producto', coerce=int, validators=[DataRequired()])
    cantidad = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1, message='Debe ser mayor a 1 producto')])
    
    #No necesitamos precio_venta_unitario aqui, lo tomaremos del Producto.precio_venta al momento de la venta
    #Si se quiere agregar un precio de venta diferente al predefinido, se agregaria aqui
    
#--- Formulario principal de Venta ---
class VentaForm(FlaskForm):
    cliente_id = SelectField('Cliente', coerce=int, validators=[DataRequired()])

    # Nuevo campo para seleccionar la moneda de la venta
    moneda_venta = SelectField('Moneda de Venta', choices=[('USD', 'USD - Dólar'), ('EUR', 'EUR - Euro')], validators=[DataRequired()])

    # Campo para mostrar la tasa de cambio actual (solo lectura, se llenará en JS)
    # Podría ser un HiddenField o un StringField read-only si quieres mostrarlo
    tasa_cambio_actual = DecimalField('Tasa de Cambio BCV (Bs. por 1 USD/EUR)', render_kw={'readonly': True}, places=4)

    productos_vendidos = FieldList(FormField(DetalleVentaForm), min_entries=1)

    submit = SubmitField('Registrar Venta')
    
#--- Formulario para crear un Nuevo Cliente ---
class ClienteForm(FlaskForm):
    nombre=StringField('Nombre', validators=[DataRequired()])
    apellido=StringField('Apellido', validators=[DataRequired()])
    cedula_rif = StringField('Cedula o Rif', validators=[DataRequired()])
    direccion=TextAreaField('Direccion')
    telefono=StringField('Telefono')
    email=StringField('Email')
    submit=SubmitField('Guardar Cliente')
                                                                                                                                                                                                                                                                                                                                                                                                                                                    
    
