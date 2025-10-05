# src/views/api_routes.py
from flask import Blueprint, jsonify, request, render_template
import logging
from threading import Thread

from src.services.clp_service import CLPService

service = CLPService



      

from src.models import CLP 
from src.db import db

clp_api = Blueprint("clp_api", __name__, url_prefix="/clp")


def _run_in_thread(target, *args, **kwargs):
    t = Thread(target=target, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t


# -------------------------
# Rotas de CLPs
# -------------------------
# @clp_api.route("/", methods=["GET"])
# def get_clps():
#     """Lista todos os CLPs no banco como dicts."""
#     return jsonify({"success": True, "clps": listar_clps_dict()})


@clp_api.route("/<ip>", methods=["GET"])
def get_clp(ip):
    """Retorna CLP específico por IP."""
    clp = service.buscar_clp_por_ip(ip)
    if not clp:
        return jsonify({"success": False, "message": "CLP não encontrado"}), 404
    return render_template("layouts/detalhes.html", clp=clp)


# @clp_api.route("/<ip>/rename", methods=["POST"])
# def rename_clp(ip):
#     """Renomeia CLP usando ORM."""
#     data = request.get_json() or {}
#     novo_nome = (data.get("novo_nome") or "").strip()
#     if not novo_nome:
#         return jsonify({"success": False, "message": "novo_nome é obrigatório"}), 400

#     clp_obj = service.buscar_clp_por_ip(ip)
#     if not clp_obj:
#         return jsonify({"success": False, "message": "CLP não encontrado"}), 404

#     try:
#         atualizar_clp(clp_obj, {"nome": novo_nome})
#         return jsonify({"success": True, "message": "Nome atualizado com sucesso"}), 200
#     except Exception as e:
#         logging.exception("Erro ao renomear CLP")
#         return jsonify({"success": False, "message": "Erro interno", "error": str(e)}), 500


# -------------------------
# Rotas de tags usando ORM
# -------------------------
@clp_api.route("/<ip>/tags", methods=["POST"])
def add_tag(ip):
    """Adiciona tag a CLP (salva no campo metadata['tags'])."""
    data = request.get_json() or {}
    tag = (data.get("tag") or "").strip()
    if not tag:
        return jsonify({"success": False, "message": "Tag vazia"}), 400

    clp_obj = service.buscar_clp_por_ip(ip)
    if not clp_obj:
        return jsonify({"success": False, "message": "CLP não encontrado"}), 404

    # pega tags existentes
    metadata = clp_obj.metadata or {}
    tags = metadata.get("tags", [])
    if tag in tags:
        return jsonify({"success": False, "message": "Tag já existe", "tags": tags}), 409

    tags.append(tag)
    metadata["tags"] = tags
    # atualizar_clp(clp_obj, {"metadata": metadata})

    return jsonify({"success": True, "message": "Tag adicionada", "tags": tags}), 200


@clp_api.route("/<ip>/tags/<tag>", methods=["DELETE"])
def remove_tag(ip, tag):
    """Remove tag de CLP."""
    clp_obj = service.buscar_clp_por_ip(ip)
    if not clp_obj:
        return jsonify({"success": False, "message": "CLP não encontrado"}), 404

    metadata = clp_obj.metadata or {}
    tags = metadata.get("tags", [])
    if tag not in tags:
        return jsonify({"success": False, "message": "Tag não encontrada", "tags": tags}), 404

    tags.remove(tag)
    metadata["tags"] = tags
    # atualizar_clp(clp_obj, {"metadata": metadata})

    return jsonify({"success": True, "message": "Tag removida", "tags": tags}), 200
