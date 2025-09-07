from flask_login import UserMixin
from .. import db
import enum
from werkzeug.security import generate_password_hash, check_password_hash


#Cria uma classe enum para os papéis
class UserRole(enum.Enum):
    USER = 'user'
    MODERATOR = "moderator"
    ADMIN = 'admin'




# UserMixin é uma classe especial do Flask-Login que já implementa
# as propriedades que o sistema de login espera (is_authenticated, etc)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    role = db.Column(db.String(50), nullable=False, default=UserRole.USER)


    def set_password(self, password):
        """Cria um hash para snha"""

        return check_password_hash(self.password_hash, password)
    

    def check_password(self, password):
        """Verifica a senha fornecida"""
        return check_password_hash(self.password_hash, password)
    

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN
    

    @property
    def is_moderator(self):
        return self.role == UserRole.MODERATOR



    def __repr__(self):
        return f"<User {self.username}>"
    

    