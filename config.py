# /config.py
import os

# Caminho base do projeto
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "src", "db")
os.makedirs(db_path, exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or "uma_chave_muito_dificil_de_adivinhar"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{os.path.join(db_path, 'app.db')}"

# Você pode ter classes para diferentes ambientes, como DevelopmentConfig, etc.