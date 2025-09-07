# /clp_app/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, Flask
from flask_login import login_user, logout_user, login_required, current_user
from .users.forms import LoginForm, RegistrationForm
from .users.models import User
from . import db, login_manager

main = Flask(__name__)

@login_manager.user_loader
def load_user(user_id):
    """Carrega o usuário da sessão."""
    return User.query.get(int(user_id))

@main.route('/')
@login_required 
def index():
    """Página principal do Dashboard."""
    return render_template('index.html')


main.mainloop()