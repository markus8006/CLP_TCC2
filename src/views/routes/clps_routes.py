from flask import Blueprint, render_template, request
from flask_login import login_required
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
