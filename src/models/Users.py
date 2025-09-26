# /clp_app/users/models.py
from flask_login import UserMixin
from src.views import db 
import enum
from werkzeug.security import generate_password_hash, check_password_hash

# Cria uma classe enum para os papéis (ótima ideia!)
class UserRole(enum.Enum):
    USER = 'user'
    MODERATOR = 'moderator'
    ADMIN = 'admin'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))

   
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER)

    def set_password(self, password : str):
        """Cria um hash para a senha. (CORRIGIDO)"""

        self.password_hash = generate_password_hash(password)

    def check_password(self, password : str):
        """Verifica a senha fornecida."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN 
    
    @property
    def is_moderator(self):
        return self.role == UserRole.MODERATOR or self.role == UserRole.ADMIN


    def __repr__(self):
        return f"<User {self.username}>"