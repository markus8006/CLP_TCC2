# /clp_app/routes.py
from flask import Blueprint, render_template
from flask_login import login_required

main = Blueprint('main', __name__)

@main.route('/')
@login_required 
def index():
    """Página principal do Dashboard, protegida por login."""
    return render_template('index.html')

# Adicione outras rotas principais do seu dashboard aqui (ex: /detalhes/<ip>)