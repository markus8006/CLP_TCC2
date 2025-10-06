from sqlalchemy.orm import Session
from typing import TypeVar, Generic, List, Optional
from src.db import db

T = TypeVar('T')

class BaseRepository(Generic[T]):
    
    def __init__(self, model_class):
        self.model_class = model_class
        self.db = db
    
    def create(self, obj: T) -> T:
        """Cria um novo registro"""
        self.db.session.add(obj)
        self.db.session.commit()
        return obj
    
    def get_by_id(self, id: int) -> Optional[T]:
        """Busca por ID"""
        return self.db.session.query(self.model_class).filter(
            self.model_class.id == id
        ).first()
    
    def get_all(self) -> List[T]:
        """Retorna todos os registros"""
        return self.db.session.query(self.model_class).all()
    
    def update(self, obj: T) -> T:
        """Atualiza registro"""
        self.db.session.commit()
        return obj
    
    def delete(self, obj: T):
        """Deleta registro"""
        self.db.session.delete(obj)
        self.db.session.commit()
    
    def delete_by_id(self, id: int) -> bool:
        """Deleta por ID"""
        obj = self.get_by_id(id)
        if obj:
            self.delete(obj)
            return True
        return False
