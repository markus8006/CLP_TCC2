# src/views/routes/main_routes.py
from flask import Blueprint, render_template, request
from flask_login import login_required
from src.services.clp_service import CLPService # <- MUDANÇA AQUI

main = Blueprint('main', __name__)

clps_por_pagina = 21

@main.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Página principal do Dashboard, protegida por login."""
    # Usa o novo serviço para buscar os dados já formatados
    clps_lista = CLPService.buscar_todos_clps()

    # ... (o resto da sua lógica de busca e paginação continua igual)
    # ...
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