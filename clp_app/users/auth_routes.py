from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from forms import LoginForm, RegistrationForm
from .models import User, UserRole
from . import db, login_manager

main = Blueprint("main", __name__)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuário ou senha inválidos.', 'danger')
            return redirect(url_for('main.login'))
        
        login_user(user)
        return redirect(url_for('main.index'))
    
    return render_template('login.html', form=form) # Crie este template

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('main.login'))

@main.route('/register', methods=['GET', 'POST'])
def register():
    # Por segurança, apenas o primeiro usuário pode se registrar livremente.
    if User.query.count() > 0:
        flash('O registro de novos usuários está desabilitado.', 'warning')
        return redirect(url_for('main.login'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # O primeiro usuário registrado será um ADMIN
        user = User(username=form.username.data, role=UserRole.ADMIN)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Usuário Administrador registrado com sucesso! Por favor, faça o login.', 'success')
        return redirect(url_for('main.login'))
        
    return render_template('register.html', form=form) # Crie este template