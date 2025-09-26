from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from src.utils.decorators.decorators import role_required
from src.controllers.clp_controller import ClpController
from src.controllers.devices_controller import DeviceController

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

    
