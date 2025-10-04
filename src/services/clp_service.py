# src/services/clp_service.py
import logging
from typing import Optional, Dict, Any, List

from src.db import db
from src.models import CLP

logger = logging.getLogger(__name__)

# --- Funções Requeridas ---

def criar_clp(dados: Dict[str, Any]) -> CLP:
    """
    Cria um novo CLP no banco de dados. Se um CLP com o mesmo IP já existir,
    ele será atualizado com os novos dados.

    Args:
        dados: Um dicionário contendo os dados do CLP (ex: 'ip', 'nome', 'porta').

    Returns:
        O objeto CLP (ORM) criado ou atualizado.
    """
    ip = dados.get("ip")
    if not ip:
        raise ValueError("O campo 'ip' é obrigatório para criar ou atualizar um CLP.")

    clp = CLP.query.filter_by(ip=ip).first()  # type: ignore

    if clp:
        # Atualiza um CLP existente
        for key, value in dados.items():
            if hasattr(clp, key): # type: ignore
                setattr(clp, key, value)
        logger.info(f"CLP com IP {ip} atualizado com sucesso.")
    else:
        # Cria um novo CLP
        clp = CLP(**dados)
        db.session.add(clp)
        logger.info(f"Novo CLP com IP {ip} criado com sucesso.")

    db.session.commit()
    return clp

def buscar_todos_clps() -> Dict[str, str]:
    """
    Busca todos os CLPs no banco de dados e retorna um dicionário
    mapeando o IP de cada CLP ao seu nome.

    Returns:
        Um dicionário no formato {ip: nome}.
    """
    clps = CLP.query.all()
    return {clp.ip: clp.nome for clp in clps}

def buscar_clp_por_ip(ip: str) -> Optional[Dict[str, Any]]:
    """
    Busca um CLP específico pelo seu endereço IP e retorna seus dados
    em formato de dicionário (JSON).

    Args:
        ip: O endereço IP do CLP a ser buscado.

    Returns:
        Um dicionário com os dados do CLP ou None se não for encontrado.
    """
    clp = CLP.query.filter_by(ip=ip).first()
    if not clp:
        return None

    return {
        "id": clp.id,
        "nome": clp.nome,
        "ip": clp.ip,
        "porta": clp.porta,
        "modelo": clp.modelo,
        "descricao": clp.descricao,
        "ativo": clp.ativo,
        # Adicione outros campos que desejar no JSON de retorno
    }

# --- Funções Auxiliares (se precisar do objeto ORM em outras partes do código) ---

def listar_clps_orm() -> List[CLP]:
    """Retorna uma lista de todos os objetos CLP (ORM)."""
    return CLP.query.all()

def buscar_clp_por_ip_orm(ip: str) -> Optional[CLP]:
    """Retorna o objeto CLP (ORM) pelo seu IP."""
    return CLP.query.filter_by(ip=ip).first()


# def buscar_por_ip(ip):
#     return buscar_clp_por_ip(ip)

# def buscar_por_ip_dict(ip):
#     return buscar_clp_por_ip(ip)

# def atualizar_clp():
#     return None

# def criar_dispositivo(dados):
#     return criar_clp(dados)