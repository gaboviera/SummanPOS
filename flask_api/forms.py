from email import message
from wtforms import validators
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SubmitField, IntegerField, DecimalField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange

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
  categoria_id = SelectField("Categoría", coerce=int, validators=[DataRequired(message="Debes seleccionar una categoria")])
  
  cantidad = IntegerField("Cantidad Inicial", default=0, validators=[DataRequired(message="La cantidad no puede ser negativa")])
  precio = DecimalField("Precio Unitario ($)", default=0.0, validators=[DataRequired(message="El precio es obligatorio"), NumberRange(min=0.0, message="El precio debe ser 0 o mayor")])
  submit = SubmitField('Guardar Producto')


# 3. Formulario para la Carga Masiva (Excel o CSV)
class CargaMasivaForm(FlaskForm):
  archivo = FileField("Subir archvio de Inventario", validators=[FileRequired(message="Debes seleccionar un archivo"),FileAllowed(['csv', 'xlsx', 'xls'], message="Solo se permiten archivos Excel (.xlsx, .xls) o CSV (.csv)")])





    


