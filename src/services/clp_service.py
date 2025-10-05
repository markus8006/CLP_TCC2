# src/services/clp_service.py
import logging
from typing import Optional, Dict, Any, List

from src.repositories.clp_repository import CLPRepository

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
        
        metadata = clp_orm.metadata or {}
        tags = set(metadata.get("tags", []))
        if tag in tags:
            return sorted(list(tags)) # Retorna a lista atual se a tag já existe
            
        tags.add(tag)
        metadata["tags"] = sorted(list(tags))
        CLPRepository.update(clp_orm, {"metadata": metadata})
        return metadata["tags"]

    @staticmethod
    def remover_tag(ip: str, tag: str) -> Optional[List[str]]:
        """Remove uma tag de um CLP."""
        clp_orm = CLPRepository.get_by_ip(ip)
        if not clp_orm:
            return None
            
        metadata = clp_orm.metadata or {}
        tags = set(metadata.get("tags", []))
        if tag not in tags:
            return None # Tag não encontrada

        tags.remove(tag)
        metadata["tags"] = sorted(list(tags))
        CLPRepository.update(clp_orm, {"metadata": metadata})
        return metadata["tags"]

    @staticmethod
    def _serialize_clp(clp: 'CLP') -> Dict[str, Any]:
        """Converte um objeto CLP ORM para um dicionário."""
        return {
            "id": clp.id,
            "nome": clp.nome,
            "ip": clp.ip,
            "porta": clp.porta,
            "modelo": clp.modelo,
            "descricao": clp.descricao,
            "ativo": clp.ativo,
            "tags": (clp.metadata or {}).get("tags", []),
            # Adicione outros campos conforme necessário
        }