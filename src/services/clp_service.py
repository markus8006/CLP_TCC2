# src/services/clp_service.py
import logging
from typing import Optional, Dict, Any, List

from src.repositories.clp_repository import CLPRepository
from src.models.CLP import CLP # Importar o modelo para type hinting

logger = logging.getLogger(__name__)

class CLPService:
    @staticmethod
    def criar_ou_atualizar_clp(dados: Dict[str, Any]) -> Dict[str, Any]:
        """Cria ou atualiza um CLP e retorna um dicionário serializado."""
        clp_orm = CLPRepository.create_or_update(dados)
        return CLPService._serialize_clp(clp_orm)

    @staticmethod
    def buscar_todos_clps() -> List[Dict[str, Any]]:
        """Busca todos os CLPs e retorna uma lista de dicionários."""
        clps_orm = CLPRepository.get_all()
        return [CLPService._serialize_clp(clp) for clp in clps_orm]

    @staticmethod
    def buscar_clp_por_ip(ip: str) -> Optional[Dict[str, Any]]:
        """Busca um CLP pelo IP e retorna um dicionário."""
        clp_orm = CLPRepository.get_by_ip(ip)
        if clp_orm:
            return CLPService._serialize_clp(clp_orm)
        return None

    @staticmethod
    def atualizar_nome_clp(ip: str, novo_nome: str) -> bool:
        """Atualiza o nome de um CLP."""
        clp_orm = CLPRepository.get_by_ip(ip)
        if not clp_orm:
            return False
        CLPRepository.update(clp_orm, {"nome": novo_nome})
        return True

    @staticmethod
    def adicionar_tag(ip: str, tag: str) -> Optional[List[str]]:
        """Adiciona uma tag a um CLP."""
        clp_orm = CLPRepository.get_by_ip(ip)
        if not clp_orm:
            return None
        
        # CORREÇÃO: Usar 'info' no lugar de 'metadata'
        info_data = clp_orm.info or {}
        tags = set(info_data.get("tags", []))
        if tag in tags:
            return sorted(list(tags)) 
            
        tags.add(tag)
        info_data["tags"] = sorted(list(tags))
        CLPRepository.update(clp_orm, {"info": info_data})
        return info_data["tags"]

    @staticmethod
    def remover_tag(ip: str, tag: str) -> Optional[List[str]]:
        """Remove uma tag de um CLP."""
        clp_orm = CLPRepository.get_by_ip(ip)
        if not clp_orm:
            return None
            
        info_data = clp_orm.info or {}
        tags = set(info_data.get("tags", []))
        if tag not in tags:
            return None

        tags.remove(tag)
        info_data["tags"] = sorted(list(tags))
        CLPRepository.update(clp_orm, {"info": info_data})
        return info_data["tags"]

    @staticmethod
    def _serialize_clp(clp: CLP) -> Dict[str, Any]:
        """Converte um objeto CLP ORM para um dicionário."""
        # CORREÇÃO: Adicionar mais campos para a UI
        return {
            "id": clp.id,
            "nome": clp.nome,
            "ip": clp.ip,
            "mac": clp.mac,
            "subnet": clp.subnet,
            "porta": clp.porta,
            "modelo": clp.modelo,
            "descricao": clp.descricao,
            "ativo": clp.ativo,
            "manual": clp.manual,
            "portas": clp.portas or [], # Garantir que seja uma lista
            "tags": (clp.info or {}).get("tags", []),
        }