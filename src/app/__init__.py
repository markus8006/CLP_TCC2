# clp_app/__init__.py
import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from src.models import *  # importa aqui para registrar no SQLAlchemy
# --- Extensões globais ---
from src.db import db
login_manager = LoginManager()

# --- Função utilitária para localizar a raiz do projeto ---
def get_project_root() -> str:
    """
    Retorna o caminho raiz do projeto.
    Compatível com execução normal (scripts .py)
    e execução em modo empacotado (PyInstaller).
    """
    if hasattr(sys, "_MEIPASS"):  # PyInstaller extrai tudo em pasta temporária
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))




# --- Configurações do Flask-Login ---
login_manager.login_view = "auth.login"
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = "info"

# --- Factory da aplicação ---
def create_app():
    app = Flask(__name__)

    # --- Configuração básica ---
    project_root = get_project_root()
    db_path = os.path.join(project_root, "db")
    os.makedirs(db_path, exist_ok=True)

    app.config.update(
        SECRET_KEY="minha_chave_super_secreta",  # TODO: puxar de .env
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(db_path, 'app.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    # Inicializar extensões
    db.init_app(app)
    login_manager.init_app(app)

    # --- Modelos e autenticação ---
    

    @login_manager.user_loader
    def load_user(user_id: str):
        """Carrega o utilizador da sessão a partir do ID."""
        return Usuario.query.get(int(user_id))

    # --- Banco de dados ---
    with app.app_context():
        db.create_all()

    # --- Blueprints ---
    from src.views.routes.main_routes import main as main_bp
    from src.views.routes.auth_routes import auth_bp
    from src.views.routes.api_routes import clp_api
    from src.views.routes.admin_routes import adm_bp
    from src.views.routes.clps_routes import clps_bp
    from src.views.routes.coleta_routes import coleta_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(clp_api)
    app.register_blueprint(adm_bp)
    app.register_blueprint(clps_bp)
    app.register_blueprint(coleta_bp)

    return app
