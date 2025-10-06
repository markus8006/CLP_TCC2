# /clp_app/users/models.py
from flask_login import UserMixin
from src.db import db 
import enum
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash


# Cria uma classe enum para os papéis (ótima ideia!)


class UserRole(enum.Enum):
    USER = 'user'
    MODERATOR = 'moderator'
    ADMIN = 'admin'



class User(db.Model):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(Enum(UserRole), default='user')  # admin, supervisor, operator
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def get_id(self):
        return self.id
    
    def is_authenticated(self):
        return self.is_active

    def is_adm(self):
        return self.role == 'admin'