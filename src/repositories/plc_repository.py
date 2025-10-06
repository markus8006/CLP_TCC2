from typing import List, Optional, Dict
from src.models.PLC import PLC
from src.repositories.base_repository import BaseRepository
from sqlalchemy import and_

class PLCRepository(BaseRepository[PLC]):
    
    def __init__(self):
        super().__init__(PLC)
    
    def get_active_plcs(self) -> List[PLC]:
        """Retorna apenas PLCs ativos"""
        return self.db.session.query(PLC).filter(PLC.is_active == True).all()
    
    def get_by_ip(self, ip_address: str) -> Optional[PLC]:
        """Busca PLC por endereço IP"""
        return self.db.session.query(PLC).filter(
            PLC.ip_address == ip_address
        ).first()
    
    def get_online_plcs(self) -> List[PLC]:
        """Retorna PLCs que estão online"""
        return self.db.session.query(PLC).filter(
            and_(PLC.is_active == True, PLC.is_online == True)
        ).all()
    
    def update_connection_status(self, plc_id: int, is_online: bool):
        """Atualiza status de conexão"""
        plc = self.get_by_id(plc_id)
        if plc:
            plc.is_online = is_online
            if is_online:
                from sqlalchemy.sql import func
                plc.last_connection = func.now()
            self.update(plc)

    def create_or_update(self, data: Dict) -> PLC:
        """
        Cria um novo PLC ou atualiza se já existir pelo IP.
        `data` é um dicionário com chaves correspondentes aos atributos do modelo PLC.
        """
        plc = self.get_by_ip(data.get("ip"))
        if plc:
            # Atualiza campos
            for key, value in data.items():
                if hasattr(plc, key):
                    setattr(plc, key, value)
            self.update(plc)
        else:
            plc = PLC(**data)
            self.create(plc)
        return plc
      
