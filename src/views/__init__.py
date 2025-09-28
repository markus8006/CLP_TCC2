# /clp_app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Declara as extensões
db = SQLAlchemy()
login_manager = LoginManager()
# Aponta para a rota de login dentro do blueprint 'auth'
login_manager.login_view = 'auth.login' 
login_manager.login_message = "Por favor, faça o login para aceder a esta página."
login_manager.login_message_category = "info"

import os, sys

def get_project_root():
    """
    Retorna o caminho raiz do projeto, funcionando tanto em modo de
    desenvolvimento (.py) quanto em modo de produção (.exe).
    """
    if hasattr(sys, '_MEIPASS'):
        # Estamos rodando em um executável criado pelo PyInstaller
        # _MEIPASS é o caminho para a pasta temporária onde tudo foi extraído
        return sys._MEIPASS
    else:
        # Estamos rodando como um script normal.
        # __file__ está em /utils/clp_manager.py, então subimos dois níveis
        # para chegar na raiz do projeto.
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app():
    app = Flask(__name__)
    
    # --- Configurações essenciais ---
    project_root = get_project_root()
    db_path = os.path.join(project_root, 'models', 'db')
    os.makedirs(db_path, exist_ok=True)

    app.config['SECRET_KEY'] = "minha_chave_super_secreta"  # ideal: puxar de .env
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(db_path, 'app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializa as extensões com a aplicação
    db.init_app(app)
    login_manager.init_app(app)

    # Importa o modelo de utilizador para ser usado no user_loader
    from src.models.Users import User

    # NOVO E ESSENCIAL: Define a função user_loader
    @login_manager.user_loader
    def load_user(user_id):
        """Carrega o utilizador da sessão a partir do user_id."""
        return User.query.get(int(user_id))

    with app.app_context():
        # Cria as tabelas do banco de dados (se não existirem)
        db.create_all()

        # --- REGISTO DOS BLUEPRINTS ---
        # Regista as rotas principais (dashboard, etc.)
        from src.views.routes.main_routes import main as main_blueprint
        app.register_blueprint(main_blueprint)

        # Regista as rotas de autenticação (login, logout, etc.)
        from src.views.routes.auth_routes import auth_bp as auth_blueprint
        app.register_blueprint(auth_blueprint)

        from src.views.routes.api_routes import clp_api
        app.register_blueprint(clp_api)

        from src.views.routes.admin_routes import adm_bp as adm_blueprint
        app.register_blueprint(adm_blueprint)

        from src.views.routes.clps_routes import clps_bp
        app.register_blueprint(clps_bp)

        from src.views.routes.coleta_routes import coleta
        app.register_blueprint(coleta)
        

    return app