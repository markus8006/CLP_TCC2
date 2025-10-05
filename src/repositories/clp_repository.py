# src/repositories/clp_repository.py
from typing import List, Optional, Dict, Any
from src.db import db
from src.models import CLP

class CLPRepository:
    @staticmethod
    def get_by_ip(ip: str) -> Optional[CLP]:
        """Busca um CLP pelo IP e retorna o objeto ORM."""
        return CLP.query.filter_by(ip=ip).first()

    @staticmethod
    def get_all() -> List[CLP]:
        """Retorna uma lista de todos os objetos CLP (ORM)."""
        return CLP.query.all()

    @staticmethod
    def create_or_update(data: Dict[str, Any]) -> CLP:
        """
        Cria um novo CLP ou atualiza um existente com base no IP.
        """
        ip = data.get("ip")
        if not ip:
            raise ValueError("O campo 'ip' é obrigatório.")

        clp = CLPRepository.get_by_ip(ip)

        if clp:
            # Atualiza
            for key, value in data.items():
                if hasattr(clp, key):
                    setattr(clp, key, value)
        else:
            # Cria
            clp = CLP(**data)
            db.session.add(clp)
        
        db.session.commit()
        return clp

    @staticmethod
    def update(clp: CLP, changes: Dict[str, Any]) -> CLP:
        """Atualiza uma instância de CLP já existente."""
        for key, value in changes.items():
            if hasattr(clp, key):
                setattr(clp, key, value)
        db.session.commit()
        return clp