from flask_login import UserMixin
from .. import db
from werkzeug.security import generate_password_hash, check_password_hash


# UserMixin é uma classe especial do Flask-Login que já implementa
# as propriedades que o sistema de login espera (is_authenticated, etc)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullabel=False)
    password_hash = db.Column(db.String(128))


    def set_password(self, password):
        """Cria um hash para snha"""

        return check_password_hash(self.password_hash, password)
    

    def check_password(self, password):
        """Verifica a senha fornecida"""
        return check_password_hash(self.password_hash, password)
    
    def __rerp__(self):
        return f"<User {self.username}>"
    