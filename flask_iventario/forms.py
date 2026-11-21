from email import message
from wtforms import validators
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SubmitField, IntegerField, DecimalField, TextAreaField, SelectField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Length, NumberRange, Regexp, Optional, InputRequired

# 1. Formulario de Inicio de Sesión
class LoginForm(FlaskForm):
  username = StringField("Usuario", validators=[DataRequired(message="El nombre del usuario es obligatorio"), Length(min=4, max=50, message="El usuario debe tener entre 4 y 50 caracteres")])
  password = PasswordField("Contraseña", validators=[DataRequired(message="La contraseña es obligatoria")])
  submit = SubmitField("Iniciar Sesión")

# 2. Formulario para Crear o Editar Productos manualmente
class ProductosForm(FlaskForm):
  nombre = StringField("Nombre del producto", validators=[DataRequired(message="El nombre es obligatorio"), Length(max=255, message="El nombre es demasiado largo")])
  descripcion = TextAreaField("Código / Descripción")
  
  # Usamos SelectField para crear listas desplegables. Coerce=int asegura que se guarden como números.
  categoria_id = SelectField("Categoría", coerce=int, default=0, validators=[Optional()])
  
  cantidad = IntegerField("Cantidad Inicial", default=0, validators=[InputRequired(message="La cantidad es obligatoria"), NumberRange(min=0, message="La cantidad no puede ser negativa")])
  precio = DecimalField("Precio Unitario ($)", default=0.0, validators=[InputRequired(message="El precio es obligatorio"), NumberRange(min=0.0, message="El precio debe ser 0 o mayor")])
  costo = DecimalField("Costo Unitario ($)", default=0.0, validators=[Optional(), NumberRange(min=0.0, message="El costo debe ser 0 o mayor")])
  proveedor_id = SelectField("Proveedor Predeterminado (Dropshipping)", coerce=int, default=0, validators=[Optional()])
  es_dropshipping = BooleanField("¿Es un producto exclusivo para Dropshipping?", default=False)
  submit = SubmitField('Guardar Producto')


# 3. Formulario para la Carga Masiva (Excel o CSV)
class CargaMasivaForm(FlaskForm):
  archivo = FileField("Subir archvio de Inventario", validators=[FileRequired(message="Debes seleccionar un archivo"),FileAllowed(['csv', 'xlsx', 'xls'], message="Solo se permiten archivos Excel (.xlsx, .xls) o CSV (.csv)")])



# 4. Formulario de Contactos
class ContactosForm(FlaskForm):
    contacto_id = HiddenField("ID de Contacto")
    tipo = SelectField('Tipo de Contacto', choices=[('Cliente', 'Cliente'), ('Proveedor', 'Proveedor'), ('Ambos', 'Ambos (Cliente y Proveedor)'), ('Contacto Usuario', 'Contacto Usuario'), ('Sin Definir', 'Sin Definir')], default='Cliente')
    nombre = StringField("Nombre o Razón Social", validators=[DataRequired(message="El nombre es obligatorio")])
    identificacion = StringField("RIF / CI", validators=[DataRequired(message="La identificación es obligatoria")])
    correo = StringField("Correo Electrónico")
    direccion = StringField("Dirección Fiscal")
    ciudad = StringField("Ciudad")
    telefono = StringField("Teléfono")
    lista_precio_id = SelectField("Tasa / Lista Preferida", coerce=int, choices=[], default=0, validators=[Optional()])
    submit = SubmitField("Guardar")

# 5. Formulario de Usuarios
class UsuariosForm(FlaskForm):
    usuario_id = HiddenField("ID de Usuario")
    username = StringField("Usuario o Correo Electrónico", validators=[
        DataRequired(message="El nombre de usuario o correo electrónico es obligatorio."),
        Length(min=3, max=50, message="El usuario debe tener entre 3 y 50 caracteres."),
        Regexp(
            r'^(?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|[a-zA-Z0-9][a-zA-Z0-9._-]{1,48}[a-zA-Z0-9]|[a-zA-Z0-9]{3,50})$',
            message="Formato inválido. Solo se permiten letras, números, puntos (.), guiones (-) o un correo válido. Sin espacios ni caracteres especiales."
        )
    ])
    password = PasswordField("Contraseña", validators=[
        Optional(),
        Length(min=6, max=100, message="La contraseña debe tener al menos 6 caracteres.")
    ])
    rol_id = SelectField("Rol de Acceso", coerce=int, validators=[DataRequired(message="Debe seleccionar un rol de acceso.")])
    activo = BooleanField("Usuario Activo")
    submit = SubmitField("Guardar Usuario")

# 6. Formulario de Configuración
class ConfiguracionForm(FlaskForm):
    logo_url = StringField("URL del Logo")
    favicon_url = StringField("URL del Favicon")
    meta_title = StringField("Título Pestaña (Meta Title)")
    submit = SubmitField("Guardar Cambios")

# 7. Formulario de Atributos
class AtributosForm(FlaskForm):
    atributo_id = HiddenField("ID del Atributo")
    nombre = StringField("Nombre del Atributo", validators=[DataRequired(message="El nombre es obligatorio")])
    submit = SubmitField("Guardar Atributo")

# 8. Formulario de Categorías
class CategoriasForm(FlaskForm):
    nombre = StringField("Nombre de la Categoría", validators=[DataRequired(message="El nombre es obligatorio")])
    submit = SubmitField("Guardar Categoría")

