from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from src.utils.decorators.decorators import role_required
from src.controllers.clp_controller import ClpController
from src.controllers.devices_controller import DeviceController
from src.services.polling_service import polling_service

clps_bp = Blueprint('clps', __name__, url_prefix='/clp')

clps_por_pagina = 21
devices_por_pagina = 21


def obter_clps_lista():
    # usa o service através do controller
    return ClpController.listar()

def obter_devices_lista():
    return DeviceController.listar()


@clps_bp.route('/<ip>')
@login_required
def detalhes_clps(ip):
    """Página de detalhes para um CLP específico."""
    # usamos o controller para obter o CLP por IP
    clp_dict = ClpController.obter_por_ip(ip)
    if not clp_dict:
        # podes trocar por 404, flash ou redirect conforme tua UI
        return render_template("clps/detalhes.html", clp={}), 404
    return render_template("clps/detalhes.html", clp=clp_dict)


@clps_bp.route("/<ip>/edit", methods=['GET', 'POST'])
@login_required
def editar_clp(ip):
    clp = ClpController.obter_por_ip(ip)
    if not clp:
        flash("CLP não encontrado", "danger")
        return redirect(url_for("clps_bp.listar_clps"))

    if request.method == "POST":
        # Campos simples (não alterar o IP!)
        clp['mac'] = request.form.get("mac")
        clp['subnet'] = request.form.get("subnet")
        clp['nome'] = request.form.get("nome")
        clp['tipo'] = request.form.get("tipo")
        clp['grupo'] = request.form.get("grupo")
        clp['status'] = request.form.get("status")
        clp['conectado'] = True if request.form.get("conectado") else False
        clp['data_registro'] = request.form.get("data_registro")

        # Metadata
        for key in clp.get('metadata', {}).keys():
            clp['metadata'][key] = request.form.get(f"metadata[{key}]")

        # Tags
        tags_text = request.form.get("tags", "")
        clp['tags'] = [t.strip() for t in tags_text.split(",") if t.strip()]

        # Portas
        portas_text = request.form.get("portas", "")
        clp['portas'] = [int(p.strip()) for p in portas_text.split(",") if p.strip().isdigit()]

        # Logs (aqui melhor acrescentar ao invés de sobrescrever)
        logs_text = request.form.get("logs", "")
        novos_logs = [l.strip() for l in logs_text.split("\n") if l.strip()]
        clp.setdefault("logs", []).extend(novos_logs)

        # Salvar no controller
        ClpController.editar_clp(ClpController.obter_por_ip(ip), clp)


        flash("CLP atualizado com sucesso!", "success")
        return redirect(url_for("clps.editar_clp", ip=clp['ip']))

    return render_template("clps/editar_clp.html", clp=clp)

    
# dentro do blueprint clps_bp
from flask import jsonify, request
from src.services.polling_service import polling_service
from src.adapters.modbus_adapter import ModbusAdapter
from src.controllers.clp_controller import ClpController

adapter = ModbusAdapter()

@clps_bp.route("/<ip>/poll/start", methods=["POST"])
@login_required
@role_required("admin")
def poll_start(ip):
    clp = ClpController.obter_por_ip(ip)
    if not clp:
        return jsonify(success=False, message="CLP não encontrado"), 404
    data = request.get_json() or {}
    port = data.get("port")
    # opcional: set port in clp antes de iniciar
    if port:
        clp.setdefault("portas", [])
        if port not in clp["portas"]:
            clp["portas"].insert(0, port)
    ok = polling_service.start_poll_for(clp)
    return jsonify(success=ok)

@clps_bp.route("/<ip>/poll/stop", methods=["POST"])
@login_required
@role_required("admin")
def poll_stop(ip):
    polling_service.stop_poll_for(ip)
    return jsonify(success=True)

@clps_bp.route("/<ip>/read", methods=["POST"])
@login_required
@role_required("admin")
def read_register(ip):
    body = request.get_json() or {}
    address = int(body.get("address", 0))
    count = int(body.get("count", 1))
    clp = ClpController.obter_por_ip(ip)
    if not clp:
        return jsonify(success=False, message="CLP não encontrado"), 404
    # tenta conectar temporariamente e ler
    if not adapter.connect(clp):
        return jsonify(success=False, message="Não conectou ao CLP"), 500
    vals = adapter.read_tag(clp, address, count)
    return jsonify(success=True, value=vals)

@clps_bp.route("/<ip>/values", methods=["GET"])
@login_required
def clp_values(ip):
    # tenta retornar dados do ClpController (registers_values + logs) ou do polling_service cache
    clp = ClpController.obter_por_ip(ip)
    data = {}
    if clp:
        data["registers_values"] = clp.get("registers_values", {})
        data["logs"] = clp.get("logs", [])
        data["status"] = clp.get("status", "Offline")
    else:
        # fallback: cache do polling_service
        cache = polling_service.get_cache()
        data["registers_values"] = cache.get(ip, {})
        data["logs"] = []
        data["status"] = "Offline"
    return jsonify(data)

@clps_bp.route("/<ip>/status", methods=["GET"])
@login_required
def clp_status(ip):
    clp = ClpController.obter_por_ip(ip)
    status = clp.get("status", "Offline") if clp else "Offline"
    return jsonify(status=status)

@clps_bp.route("/<ip>/tags/assign", methods=["POST"])
@login_required
@role_required("admin")
def assign_tag(ip):
    data = request.get_json() or {}
    tag = data.get("tag")
    if not tag:
        return jsonify(success=False, message="Tag vazia"), 400
    clp = ClpController.obter_por_ip(ip)
    if not clp:
        return jsonify(success=False, message="CLP não encontrado"), 404
    clp.setdefault("tags", [])
    if tag not in clp["tags"]:
        clp["tags"].append(tag)
    ClpController.editar_clp(ClpController.obter_por_ip(ip), clp)
    return jsonify(success=True)

@clps_bp.route("/<ip>/tags/remove", methods=["POST"])
@login_required
@role_required("admin")
def remove_tag(ip):
    data = request.get_json() or {}
    tag = data.get("tag")
    clp = ClpController.obter_por_ip(ip)
    if clp and tag in clp.get("tags", []):
        clp["tags"].remove(tag)
        ClpController.editar_clp(ClpController.obter_por_ip(ip), clp)
        return jsonify(success=True)
    return jsonify(success=False, message="Tag não encontrada"), 404

@clps_bp.route("/<ip>/edit-name", methods=["POST"])
@login_required
@role_required("admin")
def edit_name(ip):
    data = request.get_json() or {}
    nome = data.get("nome", "").strip()
    if not nome:
        return jsonify(success=False, message="Nome vazio"), 400
    clp = ClpController.obter_por_ip(ip)
    if not clp:
        return jsonify(success=False, message="CLP não encontrado"), 404
    clp['nome'] = nome
    ClpController.editar_clp(ClpController.obter_por_ip(ip), clp)
    return jsonify(success=True)
