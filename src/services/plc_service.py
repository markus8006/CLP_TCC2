# src/services/clp_service.py
import logging
from typing import Optional, Dict, Any, List

from src.repositories.plc_repository import PLCRepository
from src.models.PLC import PLC # Importar o modelo para type hinting

repository = PLCRepository()

logger = logging.getLogger(__name__)

class CLPService:


    @staticmethod
    def criar_ou_atualizar_clp(dados: Dict[str, Any]) -> Dict[str, Any]:
        """Cria ou atualiza um CLP e retorna um dicionário serializado."""
        clp_orm = repository.create_or_update(dados)
        return CLPService._serialize_clp(clp_orm)

    @staticmethod
    def buscar_todos_clps() -> List[Dict[str, Any]]:
        """Busca todos os CLPs e retorna uma lista de dicionários."""
        clps_orm = repository.get_all()
        # Garante que a lista retornada seja de dicionários
        return [CLPService._serialize_clp(clp) for clp in clps_orm]

    @staticmethod
    def buscar_clp_por_ip(ip: str) -> Optional[Dict[str, Any]]:
        """Busca um CLP pelo IP e retorna um dicionário."""
        clp_orm = repository.get_by_ip(ip)
        if clp_orm:
            return CLPService._serialize_clp(clp_orm)
        return None

    @staticmethod
    def atualizar_nome_clp(ip: str, novo_nome: str) -> bool:
        """Atualiza o nome de um CLP."""
        clp_orm = repository.get_by_ip(ip)
        if not clp_orm:
            return False
        PLCRepository.update(clp_orm, {"nome": novo_nome})
        return True

    @staticmethod
    def adicionar_tag(ip: str, tag: str) -> Optional[List[str]]:
        """Adiciona uma tag a um CLP."""
        clp_orm = PLCRepository.get_by_ip(ip)
        if not clp_orm:
            return None
        
        # CORREÇÃO: Usar 'info' no lugar de 'metadata'
        info_data = clp_orm.info or {}
        tags = set(info_data.get("tags", []))
        if tag in tags:
            return sorted(list(tags)) 
            
        tags.add(tag)
        info_data["tags"] = sorted(list(tags))
        PLCRepository.update(clp_orm, {"info": info_data})
        return info_data["tags"]

    @staticmethod
    def remover_tag(ip: str, tag: str) -> Optional[List[str]]:
        """Remove uma tag de um CLP."""
        clp_orm = PLCRepository.get_by_ip(ip)
        if not clp_orm:
            return None
            
        info_data = clp_orm.info or {}
        tags = set(info_data.get("tags", []))
        if tag not in tags:
            return None

        tags.remove(tag)
        info_data["tags"] = sorted(list(tags))
        PLCRepository.update(clp_orm, {"info": info_data})
        return info_data["tags"]

    @staticmethod
    def _serialize_clp(clp: PLC) -> Dict[str, Any]:
        """Converte um objeto CLP ORM para um dicionário com as chaves corretas para o template."""
        # CORREÇÃO: Usar os nomes de atributos que existem no seu modelo PLC
        return {
            "id": clp.id,
            "nome": clp.name,          # Correto: clp.name
            "ip": clp.ip_address,     # Correto: clp.ip_address
            "mac": clp.mac,
            "subnet": clp.subnet,
            "portas": clp.portas or [], # Garante que seja uma lista
            "descricao": f"Protocolo: {clp.protocol}, ID: {clp.unit_id}", # Exemplo de descrição
            # "tags": (clp.info or {}).get("tags", []), # Assumindo que 'tags' vivem num campo JSON 'info'
        }
    
    
