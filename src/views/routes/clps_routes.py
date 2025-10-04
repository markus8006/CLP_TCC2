# src/views/clps_routes.py  (substitua o conteúdo antigo por este)
import ast
import logging
from flask import Blueprint, jsonify, request
from flask_login import login_required
from typing import List

from src.db import db

# Modelos principais
from src.models.CLP import CLP, CLPConfigRegistrador, HistoricoLeitura
# modelos opcionais / relacionados
try:
    from src.models.Leitura import Leitura
except Exception:
    Leitura = None
try:
    from src.models.Sensor import Sensor
except Exception:
    Sensor = None

from src.controllers.clp_controller import (
    obter_por_ip,
    atualizar_clp,
    listar,
    assign_tag_to_clp,
    remove_tag_from_clp,
    get_historico_valores,
    get_recent_logs,
)





# role_required pode estar em locais diferentes; tenta importar e cria fallback
from src.utils.decorators.decorators import role_required


# CLP log model opcional
try:
    from src.models.log import CLPLog
except Exception:
    CLPLog = None

clps_bp = Blueprint("clps", __name__)

logger = logging.getLogger(__name__)


@clps_bp.route("/<ip>/values", methods=["GET"])
@login_required
def clp_values(ip):
    """
    Retorna:
      {
        "registers_values": { "<nome_variavel>": [val1, val2, ...], ... },
        "logs": [ { "msg": "...", "timestamp": "..." }, ... ],
        "status": "Online"|"Offline"
      }
    Usa HistoricoLeitura para compor os valores por config (nome_variavel).
    """
    clp = CLP.query.filter_by(ip=ip).first()
    data = {}

    if not clp:
        data["registers_values"] = {}
        data["logs"] = []
        data["status"] = "Offline"
        return jsonify(data), 200

    # --- registers_values: para cada config do CLP pegamos últimas N leituras ---
    registers_values = {}
    try:
        # limite de valores por variável (ajuste se quiser)
        LIMIT_PER_VAR = 20
        for cfg in getattr(clp, "configs", []) or []:
            nome = cfg.nome_variavel or f"cfg_{cfg.id}"
            # pega leituras mais recentes para esta config
            q = (
                HistoricoLeitura.query
                .filter_by(clp_id=clp.id, config_id=cfg.id)
                .order_by(HistoricoLeitura.timestamp.desc())
                .limit(LIMIT_PER_VAR)
                .all()
            )
            # transforma e ordena do mais antigo para o mais novo
            vals = []
            for r in q[::-1]:  # q vem do mais novo -> mais antigo; invertemos
                v = r.valor
                # tenta converter para int quando for inteiro
                try:
                    if float(v).is_integer():
                        vals.append(int(v))
                    else:
                        vals.append(float(v))
                except Exception:
                    # fallback: usa como veio
                    vals.append(v)
            registers_values[nome] = vals
    except Exception:
        logger.exception("Erro montando registers_values")
        registers_values = {}

    data["registers_values"] = registers_values

    # --- logs: usa CLPLog se existir (campo esperado: clp_id, mensagem/data) ---
    logs_out: List[dict] = []
    try:
        if CLPLog is not None:
            logs = (
                CLPLog.query
                .filter_by(clp_id=clp.id)
                .order_by(CLPLog.data.desc())
                .limit(50)
                .all()
            )
            # retorna em ordem cronológica ascendente (mais antigo primeiro)
            for log in logs[::-1]:
                data_ts = getattr(log, "data", None)
                logs_out.append({
                    "msg": getattr(log, "mensagem", getattr(log, "log", "")),
                    "timestamp": data_ts.isoformat() if getattr(data_ts, "isoformat", None) else str(data_ts)
                })
        else:
            # Se não houver CLPLog, tenta usar HistoricoLeitura como fallback (pegar timestamps recentes)
            recent = (
                HistoricoLeitura.query
                .filter_by(clp_id=clp.id)
                .order_by(HistoricoLeitura.timestamp.desc())
                .limit(20)
                .all()
            )
            for r in recent[::-1]:
                logs_out.append({
                    "msg": f"Leitura: config_id={r.config_id} valor={r.valor}",
                    "timestamp": r.timestamp.isoformat() if getattr(r.timestamp, "isoformat", None) else str(r.timestamp)
                })
    except Exception:
        logger.exception("Erro buscando logs")
        logs_out = []

    data["logs"] = logs_out

    data["status"] = getattr(clp, "status", "Offline") or "Offline"

    return jsonify(data), 200


@clps_bp.route("/<ip>/status", methods=["GET"])
@login_required
def clp_status(ip):
    clp = obter_por_ip(ip)
    status = getattr(clp, "status", "Offline") if clp else "Offline"
    return jsonify(status=status), 200



@clps_bp.route("/<ip>/tags/assign", methods=["POST"])
@login_required
@role_required("admin")
def assign_tag(ip):
    """
    Associa uma tag ao CLP. As tags são guardadas em metadata['tags'] do objeto CLP.
    """
    data = request.get_json() or {}
    tag = (data.get("tag") or "").strip()
    if not tag:
        return jsonify(success=False, message="Tag vazia"), 400

    clp_obj = obter_por_ip(ip)  # ORM object
    if not clp_obj:
        return jsonify(success=False, message="CLP não encontrado"), 404

    # garante metadata como dict
    metadata = getattr(clp_obj, "metadata", {}) or {}
    tags = set(metadata.get("tags", []))
    if tag in tags:
        return jsonify(success=False, message="Tag já existente", tags = sorted(list(tags))), 409

    tags.add(tag)
    metadata["tags"] = sorted(list(tags))

    # atualiza via device_service
    try:
        atualizar_clp(clp_obj, {"metadata": metadata})
        return jsonify(success=True, tags=metadata["tags"]), 200
    except Exception as e:
        logger.exception("Erro salvando tag")
        return jsonify(success=False, message="Erro interno ao salvar tag", error=str(e)), 500


@clps_bp.route("/<ip>/tags/remove", methods=["POST"])
@login_required
@role_required("admin")
def remove_tag(ip):
    data = request.get_json() or {}
    tag = (data.get("tag") or "").strip()
    if not tag:
        return jsonify(success=False, message="Tag vazia"), 400

    clp_obj = obter_por_ip(ip)
    if not clp_obj:   
        return jsonify(success=False, message="CLP não encontrado"), 404

    metadata = getattr(clp_obj, "metadata", {}) or {}
    tags = set(metadata.get("tags", []))
    if tag not in tags:
        return jsonify(success=False, message="Tag não encontrada", tags=sorted(list(tags))), 404

    tags.remove(tag)
    metadata["tags"] = sorted(list(tags))
    try:
        atualizar_clp(clp_obj, {"metadata": metadata})
        return jsonify(success=True, tags=metadata["tags"]), 200
    except Exception:
        logger.exception("Erro removendo tag")
        return jsonify(success=False, message="Erro interno ao salvar alterações"), 500


@clps_bp.route("/<ip>/edit-name", methods=["POST"])
@login_required
@role_required("admin")
def edit_name(ip):
    data = request.get_json() or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify(success=False, message="Nome vazio"), 400

    clp_obj = obter_por_ip(ip)
    if not clp_obj:
        return jsonify(success=False, message="CLP não encontrado"), 404

    try:
        atualizar_clp(clp_obj, {"nome": nome})
        return jsonify(success=True), 200
    except Exception:
        logger.exception("Erro editando nome")
        return jsonify(success=False, message="Erro interno ao salvar alterações"), 500
