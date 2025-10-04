# src/views/main_routes.py
from flask import Blueprint, render_template, request
from flask_login import login_required
from src.controllers.clp_controller import ClpController
# from src.controllers.devices_controller import DeviceController

main = Blueprint('main', __name__)

clps_por_pagina = 21
devices_por_pagina = 21

def obter_clps_lista():
    # usa o service através do controller
    return ClpController.listar()

# def obter_devices_lista():
#     return DeviceController.listar()

@main.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Página principal do Dashboard, protegida por login."""
    clps_lista = obter_clps_lista() or []

    # --- Garantir que clps_lista é uma lista (evita KeyError ao fatiar) ---
    if not isinstance(clps_lista, list):
        try:
            clps_lista = list(clps_lista)
        except TypeError:
            # Se for um único objeto ou algo inesperado, torne-o numa lista
            clps_lista = [clps_lista]

    search_term = ""
    tag_term = ""

    if request.method == 'POST':
        search_term = request.form.get("buscar_clp", "").lower()
        tag_term = request.form.get("buscar_tag", "").lower()

        if search_term:
            clps_lista = [
                clp for clp in clps_lista
                if search_term in (clp.get('nome') or '').lower()
            ]

        if tag_term:
            clps_lista = [
                clp for clp in clps_lista
                if any(tag_term in tag.lower() for tag in clp.get('tags', []))
            ]

    # paginação
    page = request.args.get('page', 1, type=int) or 1
    inicio = (page - 1) * clps_por_pagina
    fim = inicio + clps_por_pagina
    clps_pagina = clps_lista[inicio:fim]
    total_paginas = (len(clps_lista) + clps_por_pagina - 1) // clps_por_pagina

    return render_template(
        'layouts/index.html',
        clps=clps_pagina,
        page=page,
        total_paginas=total_paginas,
        valor=clps_por_pagina,
        search_term=search_term,
        tag_term=tag_term
    )



# @main.route("/devices")
# def todos_dispositivos():
#     devices_lista = obter_devices_lista()
#     search_term = ""
#     tag_term = ""

#     # if request.method == 'POST':
#     #     search_term = request.form.get("buscar_clp", "").lower()
#     #     tag_term = request.form.get("buscar_tag", "").lower()

#     #     if search_term:
#     #         clps_lista = [
#     #             clp for clp in clps_lista
#     #             if search_term in (clp.get('nome') or '').lower()
#     #         ]

#     #     if tag_term:
#     #         clps_lista = [
#     #             clp for clp in clps_lista
#     #             if any(tag_term in tag.lower() for tag in clp.get('tags', []))
#     #         ]

#     # paginação
#     page = request.args.get('page', 1, type=int) or 1
#     inicio = (page - 1) * devices_por_pagina
#     fim = inicio + devices_por_pagina
#     devices_pagina = devices_lista[inicio:fim]
#     total_paginas = (len(devices_lista) + devices_por_pagina - 1) // devices_por_pagina

#     return render_template(
#         'index.html',
#         clps=devices_pagina,
#         page=page,
#         total_paginas=total_paginas,
#         valor=devices_por_pagina,
#         search_term=search_term,
#         tag_term=tag_term
#     )




