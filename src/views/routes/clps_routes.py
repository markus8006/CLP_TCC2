# src/views/routes/clps_routes.py
from flask import Blueprint, jsonify, request
from flask_login import login_required
from src.services.clp_service import CLPService
from src.utils.decorators.decorators import role_required

clps_bp = Blueprint("clps", __name__, url_prefix="/clps")

@clps_bp.route("/<ip>/values", methods=["GET"])
@login_required
def clp_values(ip):
    # Esta rota pode ser mais complexa e ter sua própria lógica de serviço
    # Por enquanto, vamos mantê-la simples
    clp = CLPService.buscar_clp_por_ip(ip)
    if not clp:
        return jsonify({"status": "Offline", "registers_values": {}, "logs": []}), 404
    
    # A lógica para buscar valores e logs deve ir para o CLPService
    # Ex: registers_values = CLPService.get_live_values(ip)
    # Ex: logs = CLPService.get_recent_logs(ip)
    
    return jsonify({
        "status": clp.get("status", "Offline"),
        "registers_values": {}, # TODO: Implementar no service
        "logs": [] # TODO: Implementar no service
    }), 200

@clps_bp.route("/<ip>/edit-name", methods=["POST"])
@login_required
@role_required("admin")
def edit_name(ip):
    data = request.get_json() or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify(success=False, message="Nome vazio"), 400

    success = CLPService.atualizar_nome_clp(ip, nome)
    if not success:
        return jsonify(success=False, message="CLP não encontrado"), 404
        
    return jsonify(success=True), 200

@clps_bp.route("/<ip>/tags/assign", methods=["POST"])
@login_required
@role_required("admin")
def assign_tag(ip):
    data = request.get_json() or {}
    tag = (data.get("tag") or "").strip()
    if not tag:
        return jsonify(success=False, message="Tag vazia"), 400

    tags = CLPService.adicionar_tag(ip, tag)
    if tags is None:
        return jsonify(success=False, message="CLP não encontrado"), 404
    
    return jsonify(success=True, tags=tags), 200

@clps_bp.route("/<ip>/tags/remove", methods=["POST"])
@login_required
@role_required("admin")
def remove_tag(ip):
    data = request.get_json() or {}
    tag = (data.get("tag") or "").strip()
    if not tag:
        return jsonify(success=False, message="Tag vazia"), 400
        
    tags = CLPService.remover_tag(ip, tag)
    if tags is None:
        return jsonify(success=False, message="CLP ou Tag não encontrada"), 404
        
    return jsonify(success=True, tags=tags), 200