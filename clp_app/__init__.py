# /clp_app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from utils.root import get_project_root # Usando sua função para compatibilidade com .exe

# Declara as extensões
db = SQLAlchemy()
login_manager = LoginManager()
# Aponta para a rota de login dentro do blueprint 'auth'
login_manager.login_view = 'auth.login' 
login_manager.login_message = "Por favor, faça o login para aceder a esta página."
login_manager.login_message_category = "info"

def create_app():
    app = Flask(__name__)
    
    # Configurações essenciais
    app.config['SECRET_KEY'] = os.urandom(24)
    PROJECT_ROOT = get_project_root()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(PROJECT_ROOT, 'clp_app/db/app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializa as extensões com a aplicação
    db.init_app(app)
    login_manager.init_app(app)

    # Importa o modelo de utilizador para ser usado no user_loader
    from .users_page.models import User

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
        from .routes import main as main_blueprint
        app.register_blueprint(main_blueprint)

        # Regista as rotas de autenticação (login, logout, etc.)
        from .users_page.auth_routes import auth_bp as auth_blueprint
        app.register_blueprint(auth_blueprint)

        from .api.routes import clp_bp
        app.register_blueprint(clp_bp)
        
        # Futuramente, registe aqui as suas rotas de API
        # from .api.routes import clp_bp
        # app.register_blueprint(clp_bp)

    return app