# src/controllers/clp_controller.py
from typing import List, Dict, Any, Optional
from src.db import db
from src.models.CLP import CLP, HistoricoLeitura  # ajuste se HistoricoLeitura estiver noutro módulo
from src.services.clp_service import (
    criar_clp,
    buscar_todos_clps,
    buscar_clp_por_ip_orm,
    listar_clps_orm,
)

import logging
logger = logging.getLogger(__name__)


def obter_por_ip(ip: str) -> Optional[CLP]:
    """Retorna o objeto ORM CLP ou None."""
    return buscar_clp_por_ip_orm(ip)


def atualizar_clp(clp_or_ip, changes: Dict[str, Any]) -> CLP:
    """
    Atualiza campos permitidos no CLP e commita.
    - clp_or_ip pode ser instancia ORM ou string ip.
    - changes é um dict com chaves como: 'nome', 'status', 'metadata' (dict).
    Retorna a instância atualizada.
    """
    if isinstance(clp_or_ip, str):
        clp = obter_por_ip(clp_or_ip)
    else:
        clp = clp_or_ip

    if not clp:
        raise ValueError("CLP não encontrado")

    # lidar com metadata: mesclar se for dict
    if 'metadata' in changes and isinstance(changes['metadata'], dict):
        md = clp.metadata or {}
        # se desejar sobrescrever completamente, troque md = changes['metadata']
        md.update(changes['metadata'])
        clp.metadata = md
        # remove metadata do changes para não tentar setar novamente
        changes = {k: v for k, v in changes.items() if k != 'metadata'}

    # setar atributos existentes
    for key, value in changes.items():
        if hasattr(clp, key):
            setattr(clp, key, value)

    db.session.add(clp)
    db.session.commit()
    # refresh opcional
    try:
        db.session.refresh(clp)
    except Exception:
        pass
    return clp


def listar() -> List[Dict[str, Any]]:
    """
    Retorna lista de dicts representando CLPs (serializável).
    Útil para paginação e filtros nas routes.
    """
    # usamos listar_clps_orm para garantir objetos ORM completos
    clps = listar_clps_orm()
    out: List[Dict[str, Any]] = []
    for c in clps:
        md = c.metadata or {}
        out.append({
            "id": c.id,
            "ip": c.ip,
            "nome": c.nome,
            "status": c.status or "Offline",
            "tags": md.get("tags", []),
            # adicione outros campos que achar útil (modelo, porta, etc)
        })
    return out


def assign_tag_to_clp(clp_or_ip, tag: str) -> List[str]:
    clp = clp_or_ip if not isinstance(clp_or_ip, str) else obter_por_ip(clp_or_ip)
    if not clp:
        raise ValueError("CLP não encontrado")
    md = clp.metadata or {}
    tags = set(md.get("tags", []))
    if tag in tags:
        raise ValueError("Tag já existente")
    tags.add(tag)
    md["tags"] = sorted(list(tags))
    clp.metadata = md
    db.session.add(clp)
    db.session.commit()
    return md["tags"]


def remove_tag_from_clp(clp_or_ip, tag: str) -> List[str]:
    clp = clp_or_ip if not isinstance(clp_or_ip, str) else obter_por_ip(clp_or_ip)
    if not clp:
        raise ValueError("CLP não encontrado")
    md = clp.metadata or {}
    tags = set(md.get("tags", []))
    if tag not in tags:
        raise KeyError("Tag não encontrada")
    tags.remove(tag)
    md["tags"] = sorted(list(tags))
    clp.metadata = md
    db.session.add(clp)
    db.session.commit()
    return md["tags"]


# Funções auxiliar para histórico / logs se precisar (pode ser extraídas para services)
def get_historico_valores(clp_id: int, config_id: int, limit: int = 20) -> List[Any]:
    q = (
        HistoricoLeitura.query
        .filter_by(clp_id=clp_id, config_id=config_id)
        .order_by(HistoricoLeitura.timestamp.desc())
        .limit(limit)
        .all()
    )
    vals = []
    for r in q[::-1]:
        v = r.valor
        try:
            if float(v).is_integer():
                vals.append(int(v))
            else:
                vals.append(float(v))
        except Exception:
            vals.append(v)
    return vals


def get_recent_logs(clp_id: int, limit: int = 50) -> List[Dict[str, str]]:
    logs_out = []
    # tenta CLPLog dinamicamente no módulo de modelos
    try:
        from src.models.log import CLPLog  # type: ignore
    except Exception:
        CLPLog = None

    if CLPLog is not None:
        logs = CLPLog.query.filter_by(clp_id=clp_id).order_by(CLPLog.data.desc()).limit(limit).all()
        for log in logs[::-1]:
            ts = getattr(log, "data", None)
            logs_out.append({
                "msg": getattr(log, "mensagem", getattr(log, "log", "")),
                "timestamp": ts.isoformat() if getattr(ts, "isoformat", None) else str(ts)
            })
    else:
        recent = (
            HistoricoLeitura.query
            .filter_by(clp_id=clp_id)
            .order_by(HistoricoLeitura.timestamp.desc())
            .limit(limit)
            .all()
        )
        for r in recent[::-1]:
            logs_out.append({
                "msg": f"Leitura: config_id={r.config_id} valor={r.valor}",
                "timestamp": r.timestamp.isoformat() if getattr(r.timestamp, "isoformat", None) else str(r.timestamp)
            })
    return logs_out
