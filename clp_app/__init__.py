from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Define a raiz do projeto para encontrar o banco de dados
basedir = os.path.abspath(os.path.dirname(__file__))

# Declara as extensões
db = SQLAlchemy()
login_manager = LoginManager()
# Define a rota para a qual usuários não logados serão redirecionados
login_manager.login_view = 'main.login' 
login_manager.login_message = "Por favor, faça o login para acessar esta página."

def create_app():
    app = Flask(__name__)
    
    # Chave secreta para proteger os formulários e a sessão
    app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-dificil-de-adivinhar'
    # Configuração do banco de dados SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializa as extensões com a aplicação
    db.init_app(app)
    login_manager.init_app(app)

    # Importa os modelos para que o SQLAlchemy possa criar as tabelas
    from . import models

    # Cria as tabelas do banco de dados, se não existirem
    with app.app_context():
        db.create_all()

    # Registra os Blueprints (nossas rotas)
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    # ... (você pode registrar seus outros blueprints aqui, como o da API)
    # from .api.routes import clp_bp
    # app.register_blueprint(clp_bp)

    return app