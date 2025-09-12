# /clp_app/routes.py
from flask import Blueprint, render_template, request
from flask_login import login_required
from utils import clp_manager


main = Blueprint('main', __name__)

clps_por_pagina = 21


def obter_clps_lista():
    return clp_manager.listar_clps()

@main.route('/', methods=['GET', 'POST'])
@login_required 
def index():
    """Página principal do Dashboard, protegida por login."""
    clps_lista = obter_clps_lista()
    search_term = ""
    tag_term = "" # <-- NOVO

    if request.method == 'POST':
        search_term = request.form.get("buscar_clp", "").lower()
        tag_term = request.form.get("buscar_tag", "").lower() # <-- NOVO

        if search_term:
            clps_lista = [
                clp for clp in clps_lista
                if search_term in clp.get('nome', '').lower()
            ]
        
        # <-- NOVO: Filtra por tag se um termo de tag for fornecido
        if tag_term:
            clps_lista = [
                clp for clp in clps_lista
                if any(tag_term in tag.lower() for tag in clp.get('tags', []))
            ]

    # ... (lógica de paginação continua a mesma)
    page = request.args.get('page', 1, type=int)
    if not page:
        page = 1
    inicio = (page - 1) * clps_por_pagina
    fim = inicio + clps_por_pagina
    clps_pagina = clps_lista[inicio:fim]
    total_paginas = (len(clps_lista) + clps_por_pagina - 1) // clps_por_pagina
    
    return render_template(
        'index.html',
        clps=clps_pagina,
        page=page,
        total_paginas=total_paginas,
        valor=clps_por_pagina,
        search_term=search_term,
        tag_term=tag_term # <-- NOVO
    )

@login_required
@main.route('/clp/<ip>')
def detalhes_clps(ip):
    """Página de detalhes para um CLP específico."""
    clp_dict = clp_manager.buscar_por_ip(ip)
    return render_template("detalhes.html", clp=clp_dict)