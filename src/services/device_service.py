# src/services/device_service.py
import logging
from typing import Optional, Dict, Any, List, Union, Iterable
from datetime import datetime
from netaddr import EUI
from src.utils.root.root import get_project_root
from src.repositories.json_repo import carregar_arquivo, salvar_arquivo
from src.models.Device import Device
from src.utils.root.paths import DEVICES_FILE, CLPS_FILE
from flask import current_app
from src.views import db
from src.models.Registers import CLP

PROJECT_ROOT = get_project_root()
logger = logging.getLogger(__name__)

# lazy load
_clps_data: Optional[List[Dict[str, Any]]] = None
_others_data: Optional[List[Dict[str, Any]]] = None

def _ensure_loaded():
    global _clps_data, _others_data
    if _clps_data is None:
        if current_app:
            _clps_data = carregar_arquivo(CLPS_FILE) or []
        else:
            _clps_data = []
    if _others_data is None:
        _others_data = carregar_arquivo(DEVICES_FILE) or []


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def buscar_todos() -> List[Dict[str, Any]]:
    _ensure_loaded()
    return list(_clps_data)


def buscar_por_ip(ip_procurado: str) -> Optional[Dict[str, Any]]:
    _ensure_loaded()
    for clp in _clps_data:
        if clp.get("ip") == ip_procurado:
            return clp
    for dev in _others_data:
        if dev.get("ip") == ip_procurado:
            return dev
    return None


def _remover_por_ip_de_lista(ip: str, lista: List[Dict[str, Any]]) -> None:
    idx = next((i for i, e in enumerate(lista) if e.get("ip") == ip), None)
    if idx is not None:
        lista.pop(idx)


def salvar_clps() -> None:
    _ensure_loaded()
    salvar_arquivo(CLPS_FILE, _clps_data)


def salvar_others() -> None:
    _ensure_loaded()
    salvar_arquivo(DEVICES_FILE, _others_data)


def _to_int_list(iterable: Optional[Iterable[Any]]) -> List[int]:
    if not iterable:
        return []
    out: List[int] = []
    for v in iterable:
        try:
            out.append(int(v))
        except Exception:
            continue
    return sorted(list(set(out)))


def criar_dispositivo(dados: dict, grupo: str = "Sem Grupo", Manual=False) -> CLP:
    """
    Cria ou atualiza um CLP no banco de dados.
    Mantém a interface compatível com a versão JSON.
    """
    ip = dados.get("ip")
    if not ip:
        logger.warning("[WARN] criar_dispositivo chamado sem IP válido.")
        return None

    # Busca no DB
    clp = CLP.query.filter_by(ip=ip).first()

    # Garantir que portas seja lista de inteiros
    portas_raw = dados.get("portas", [])
    portas_list = [int(p) for p in portas_raw if str(p).isdigit()]

    tipo = dados.get("tipo", "CLP") if Manual else "CLP"

    if clp:
        # Atualiza campos
        clp.nome = dados.get("nome", clp.nome)
        clp.subnet = dados.get("subnet", clp.subnet)
        clp.portas = portas_list
        clp.grupo = grupo or getattr(clp, "grupo", "Sem Grupo")
        clp.protocolo = dados.get("protocolo", clp.protocolo)
        db.session.commit()
        logger.info(f"[INFO] CLP {ip} atualizado no banco de dados.")
        return clp

    # Cria novo
    clp = CLP(
        ip=ip,
        nome=dados.get("nome") or f"{tipo}_{ip}",
        tipo=tipo,
        subnet=dados.get("subnet"),
        portas=portas_list,
        grupo=grupo,
        protocolo=dados.get("protocolo", "modbus"),
        status="Offline"
    )
    db.session.add(clp)
    db.session.commit()
    logger.info(f"[INFO] Novo CLP {ip} criado no banco de dados.")
    return clp



def listar_clps() -> List[Dict[str, Any]]:
    _ensure_loaded()
    return list(_clps_data)


def listar_devices() -> List[Dict[str, Any]]:
    _ensure_loaded()
    return list(_others_data)


def atualizar_clp(clp_antigo: Union[CLP, str], dados_novos: dict) -> CLP:
    """
    Atualiza um CLP existente no banco de dados.
    clp_antigo pode ser um objeto CLP ou um IP.
    """
    if isinstance(clp_antigo, str):
        clp = CLP.query.filter_by(ip=clp_antigo).first()
    elif isinstance(clp_antigo, CLP):
        clp = clp_antigo
    else:
        return None

    if not clp:
        logger.warning(f"[WARN] Nenhum CLP encontrado para atualização: {clp_antigo}")
        return None

    # Atualiza campos do banco
    for key, value in dados_novos.items():
        if key == "portas":
            clp.portas = ",".join(map(str, value))
        elif hasattr(clp, key):
            setattr(clp, key, value)

    db.session.commit()
    logger.info(f"[INFO] CLP {clp.ip} atualizado com novos dados: {list(dados_novos.keys())}")
    return clp
