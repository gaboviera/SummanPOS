from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from forms import LoginForm
from services.auth_services import verificar_credenciales

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Si el usuario ya está logueado, mandarlo al dashboard
    if current_user.is_authenticated:
        return redirect(url_for("inventario.dashboard"))

    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        usuario = verificar_credenciales(username, password)
        
        if usuario:
            # Login exitoso
            login_user(usuario)
            flash(f"¡Bienvenido de nuevo, {usuario.username}!", "success")
            
            # Redirigir a la página que intentó acceder antes del login, o al dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for("inventario.dashboard"))
        else:
            flash("Usuario o contraseña incorrectos", "danger")

    return render_template("login.html", form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Has cerrado sesión exitosamente.", "info")
    return redirect(url_for("auth.login"))
