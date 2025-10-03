# src/services/device_service.py
import logging
from typing import Optional, Dict, Any, List, Union, Iterable
from datetime import datetime

from src.db import db  # ajuste se o seu DB estiver noutro lugar (ex: from clp_app import db)

# Tenta importar modelos nos caminhos esperados; ajuste conforme o seu projeto
try:
    from src.models.clp import CLP, CLPConfigRegistrador
except Exception:
    # fallback: tenta nomes alternativos
    try:
        from src.models import CLP, CLPConfigRegistrador
    except Exception:
        CLP = None
        CLPConfigRegistrador = None

try:
    from src.models.log import CLPLog
except Exception:
    CLPLog = None

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.utcnow()


def _to_int_list(iterable: Optional[Iterable[Any]]) -> List[int]:
    """
    Normaliza entradas para uma list[int]. Aceita lista de str, lista de int, string "1,2,3".
    """
    if not iterable:
        return []
    # se for string com vírgulas
    if isinstance(iterable, str):
        parts = [p.strip() for p in iterable.split(",") if p.strip()]
        iterable = parts
    out: List[int] = []
    for v in iterable:
        try:
            out.append(int(v))
        except Exception:
            continue
    return sorted(list(set(out)))


# ------------------------------
# Conversores / Helpers
# ------------------------------
def _normalize_portas_field(portas_field) -> List[int]:
    """Retorna lista de inteiros a partir de várias representações possíveis."""
    return _to_int_list(portas_field)


def _clp_to_dict(clp: "CLP") -> Dict[str, Any]:
    """Converte um objeto CLP (SQLAlchemy) para dict JSON-serializável."""
    if clp is None:
        return {}
    # portas pode ser JSON (list) ou string CSV
    portas = getattr(clp, "portas", None) or []
    if isinstance(portas, str):
        portas = _to_int_list(portas)
    metadata = getattr(clp, "metadata", {}) or {}
    data_reg = getattr(clp, "data_registro", None)
    data_reg_s = data_reg.isoformat() if data_reg is not None else None

    # se tiver configs, incluir sumário leve (não incluir configs inteiras para performance)
    configs = getattr(clp, "configs", None)
    configs_summary = []
    if configs:
        for c in configs:
            configs_summary.append({
                "id": c.id,
                "tipo": c.tipo,
                "endereco_inicial": c.endereco_inicial,
                "quantidade": c.quantidade,
                "intervalo_leitura": c.intervalo_leitura,
                "nome_variavel": c.nome_variavel,
                "ativo": c.ativo
            })

    return {
        "id": clp.id,
        "ip": clp.ip,
        "nome": clp.nome,
        "tipo": clp.tipo,
        "protocolo": clp.protocolo,
        "grupo": clp.grupo,
        "subnet": clp.subnet,
        "portas": portas,
        "metadata": metadata,
        "status": clp.status,
        "data_registro": data_reg_s,
        "configs": configs_summary
    }


# ------------------------------
# CRUD CLP
# ------------------------------
def listar_clps_dict() -> List[Dict[str, Any]]:
    """Retorna todos os CLPs do banco como lista de dicts (pronto para JSON)."""
    if CLP is None:
        logger.error("Modelo CLP não disponível.")
        return []
    clps = CLP.query.all()
    return [_clp_to_dict(c) for c in clps]


def listar_clps() -> List["CLP"]:
    """Retorna objetos CLP (ORM)."""
    if CLP is None:
        return []
    return CLP.query.all()


def buscar_por_ip(ip: str) -> Optional["CLP"]:
    """Retorna o objeto CLP por IP ou None."""
    if not ip or CLP is None:
        return None
    return CLP.query.filter_by(ip=ip).first()


def buscar_por_ip_dict(ip: str) -> Optional[Dict[str, Any]]:
    """Retorna o CLP como dict (ou None)."""
    clp = buscar_por_ip(ip)
    return _clp_to_dict(clp) if clp else None


def criar_dispositivo(dados: dict, grupo: str = "Sem Grupo", manual: bool = False) -> Optional["CLP"]:
    """
    Cria ou atualiza um CLP no banco.
    - dados: dict com chaves ip, nome, subnet, portas, protocolo, tipo, metadata, status
    - retorna objeto CLP (ORM)
    """
    if CLP is None:
        logger.error("Modelo CLP não disponível. Não é possível criar dispositivo.")
        return None

    ip = dados.get("ip")
    if not ip:
        logger.warning("criar_dispositivo chamado sem IP válido.")
        return None

    # normaliza portas
    portas_list = _to_int_list(dados.get("portas") or dados.get("ports") or [])

    tipo = dados.get("tipo", "CLP") if manual else dados.get("tipo", "CLP")

    clp = CLP.query.filter_by(ip=ip).first()
    if clp:
        # atualiza
        clp.nome = dados.get("nome", clp.nome)
        clp.subnet = dados.get("subnet", clp.subnet)
        if portas_list:
            try:
                clp.portas = portas_list
            except Exception:
                clp.portas = ",".join(map(str, portas_list))
        clp.grupo = grupo or getattr(clp, "grupo", "Sem Grupo")
        clp.protocolo = dados.get("protocolo", clp.protocolo)
        clp.tipo = tipo or clp.tipo
        clp.status = dados.get("status", clp.status)
        # metadata merge
        meta = dados.get("metadata")
        if isinstance(meta, dict):
            existing = getattr(clp, "metadata", {}) or {}
            existing.update(meta)
            clp.metadata = existing
        db.session.commit()
        logger.info(f"CLP {ip} atualizado.")
        return clp

    # cria novo
    novo = CLP(
        ip=ip,
        nome=dados.get("nome") or f"{tipo}_{ip}",
        tipo=tipo,
        subnet=dados.get("subnet"),
        portas=portas_list,
        grupo=grupo,
        protocolo=dados.get("protocolo", "modbus"),
        status=dados.get("status", "Offline"),
        metadata=dados.get("metadata") or {}
    )
    db.session.add(novo)
    db.session.commit()
    logger.info(f"Novo CLP {ip} criado (id={novo.id}).")
    return novo


def atualizar_clp(clp_antigo: Union["CLP", str], dados_novos: dict) -> Optional["CLP"]:
    """
    Atualiza CLP existente. clp_antigo pode ser IP (str) ou objeto CLP.
    """
    if CLP is None:
        logger.error("Modelo CLP não disponível.")
        return None

    if isinstance(clp_antigo, str):
        clp = CLP.query.filter_by(ip=clp_antigo).first()
    elif isinstance(clp_antigo, CLP):
        clp = clp_antigo
    else:
        clp = None

    if not clp:
        logger.warning(f"Nenhum CLP encontrado para atualizar: {clp_antigo}")
        return None

    for key, value in dados_novos.items():
        if key == "portas":
            portas_list = _to_int_list(value)
            try:
                clp.portas = portas_list
            except Exception:
                clp.portas = ",".join(map(str, portas_list))
        elif key == "metadata" and isinstance(value, dict):
            existing = getattr(clp, "metadata", {}) or {}
            existing.update(value)
            clp.metadata = existing
        elif hasattr(clp, key):
            setattr(clp, key, value)
        else:
            # salva campo desconhecido em metadata, se possível
            try:
                meta = getattr(clp, "metadata", {}) or {}
                meta[key] = value
                clp.metadata = meta
            except Exception:
                pass

    db.session.commit()
    logger.info(f"CLP {clp.ip} atualizado: campos {list(dados_novos.keys())}")
    return clp


def remover_clp_por_ip(ip: str) -> bool:
    """Remove CLP por IP; retorna True se removido."""
    if CLP is None or not ip:
        return False
    clp = CLP.query.filter_by(ip=ip).first()
    if not clp:
        return False
    db.session.delete(clp)
    db.session.commit()
    logger.info(f"CLP {ip} removido.")
    return True


# ------------------------------
# Logs do CLP
# ------------------------------
def adicionar_log(clp_id: int, nivel: str, mensagem: str) -> Optional["CLPLog"]:
    """
    Adiciona log para CLP. Requer modelo CLPLog existir.
    """
    if CLPLog is None:
        logger.error("Modelo CLPLog não encontrado. Não é possível gravar logs.")
        return None
    log = CLPLog(
        clp_id=clp_id,
        nivel=(nivel or "INFO").upper(),
        mensagem=mensagem,
        data=_now()
    )
    db.session.add(log)
    db.session.commit()
    return log


def listar_logs(clp_id: int, limit: int = 200) -> List[Dict[str, Any]]:
    """Lista logs de um CLP ordenados por data desc."""
    if CLPLog is None:
        logger.warning("CLPLog não disponível. Retornando lista vazia.")
        return []
    q = CLPLog.query.filter_by(clp_id=clp_id).order_by(CLPLog.data.desc()).limit(limit)
    return [
        {"id": r.id, "clp_id": r.clp_id, "nivel": r.nivel, "mensagem": r.mensagem,
         "data": r.data.isoformat() if getattr(r.data, "isoformat", None) else str(r.data)}
        for r in q
    ]


# ------------------------------
# Helpers para polling / configs
# ------------------------------
def listar_clps_para_polling() -> List[Dict[str, Any]]:
    """
    Retorna CLPs ativos com suas configs (somente configs ativas),
    prontos para o serviço de polling consumir.
    """
    if CLP is None or CLPConfigRegistrador is None:
        return []

    clps = CLP.query.filter_by(ativo=True).all() if hasattr(CLP, "ativo") else CLP.query.all()
    out = []
    for c in clps:
        configs = []
        for cfg in getattr(c, "configs", []) or []:
            if getattr(cfg, "ativo", True):
                configs.append({
                    "id": cfg.id,
                    "tipo": cfg.tipo,
                    "endereco_inicial": cfg.endereco_inicial,
                    "quantidade": cfg.quantidade,
                    "intervalo_leitura": cfg.intervalo_leitura,
                    "nome_variavel": cfg.nome_variavel,
                    "unidade": cfg.unidade
                })
        out.append({
            "id": c.id,
            "ip": c.ip,
            "porta": getattr(c, "porta", None) or getattr(c, "port", None) or None,
            "protocolo": c.protocolo,
            "portas": _normalize_portas_field(getattr(c, "portas", [])),
            "configs": configs
        })
    return out


def get_configs_for_clp(clp_id: int) -> List[Dict[str, Any]]:
    """Retorna as configs ativas (em dict) para um CLP específico."""
    if CLPConfigRegistrador is None:
        return []
    q = CLPConfigRegistrador.query.filter_by(clp_id=clp_id, ativo=True).all()
    return [{
        "id": cfg.id,
        "tipo": cfg.tipo,
        "endereco_inicial": cfg.endereco_inicial,
        "quantidade": cfg.quantidade,
        "intervalo_leitura": cfg.intervalo_leitura,
        "nome_variavel": cfg.nome_variavel,
        "unidade": cfg.unidade
    } for cfg in q]
