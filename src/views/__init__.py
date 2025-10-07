import os
import sys
from flask import Flask
from flask_login import LoginManager
from config import Config
from flask_migrate import Migrate
import time

from src.db import db
from src.models import PLC, Reading, Register, User, UserRole

login_manager = LoginManager()

login_manager.login_view = "auth.login"
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = "info"

def get_project_root() -> str:
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def create_app(config_class=Config):
    project_root = get_project_root()
    template_folder = os.path.join(project_root, "views", "templates")
    static_folder = os.path.join(project_root, "views", "static")
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder, static_url_path='/static')

    db_path = os.path.join(project_root, "db")
    os.makedirs(db_path, exist_ok=True)
    app.config.from_object(config_class)

    app.config.update(
        SECRET_KEY="minha_chave_super_secreta",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(db_path, 'app.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)
    time.sleep(1)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    with app.app_context():
        from src.models import PLC, Reading, Register, User, UserRole
        db.create_all()

    # Blueprints 
    from src.views.routes.main_routes import main as main_bp 
    from src.views.routes.blueprints.auth_routes import auth_bp 
    from src.views.routes.blueprints.api_routes import clp_api 
    from src.views.routes.blueprints.admin_routes import adm_bp 
    from src.views.routes.blueprints.plc_routes import plc_bp 
    from src.views.routes.blueprints.coleta_routes import coleta as coleta_bp 
    app.register_blueprint(main_bp) 
    app.register_blueprint(auth_bp) 
    app.register_blueprint(clp_api) 
    app.register_blueprint(adm_bp) 
    app.register_blueprint(plc_bp) 
    app.register_blueprint(coleta_bp)

    migrate = Migrate(app, db)
    return app
