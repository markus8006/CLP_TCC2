# /clp_app/users/auth_routes.py
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import sys
from pathlib import Path

from src.views.forms import LoginForm, RegistrationForm
from src.models.Users import User, UserRole
from src.utils.decorators.decorators import role_required
from src.views import db 

# Cria um Blueprint para as rotas de autenticação
auth_bp = Blueprint('auth', __name__)




@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Utilizador ou senha inválidos.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user)
        # Redireciona para a página principal (que está no blueprint 'main')
        return redirect(url_for('main.index'))
    
    return render_template('users_page/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão encerrada.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Por segurança, apenas o primeiro utilizador pode-se registar livremente.
    if User.query.count() > 0 and not current_user.is_authenticated:
        flash('O registo de novos utilizadores está desabilitado.', 'warning')
        return redirect(url_for('auth.login'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # O primeiro utilizador registado será um ADMIN
        user = User(username=form.username.data, role=UserRole(form.user_type.data))
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Utilizador Administrador registado com sucesso! Por favor, faça o login.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('users_page/register.html', form=form)