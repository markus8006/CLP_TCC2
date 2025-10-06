# src/views/routes/main_routes.py
from flask import Blueprint, render_template, request
from flask_login import login_required
# Garanta que o nome do arquivo importado esteja correto
from src.services.plc_service import CLPService

main = Blueprint('main', __name__)

# REMOVA a criação da instância daqui
# DE: service = CLPService()

clps_por_pagina = 21

@main.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Página principal do Dashboard, protegida por login."""
    
    # PARA: Chame o método diretamente da CLASSE.
    # Isso garante que você use a versão @staticmethod que retorna DICIONÁRIOS.
    clps_lista = CLPService().buscar_todos_clps()

    # O resto do seu código agora funcionará sem erros,
    # pois `clps_lista` será uma lista de dicionários.
    search_term = request.form.get("buscar_clp", "").lower()
    if search_term:
        clps_lista = [
            clp for clp in clps_lista
            if search_term in (clp.get('nome') or '').lower()
        ]
    
    # ... O resto da função continua igual ...
    page = request.args.get('page', 1, type=int)
    inicio = (page - 1) * clps_por_pagina
    fim = inicio + clps_por_pagina
    clps_pagina = clps_lista[inicio:fim]
    total_paginas = max(1, (len(clps_lista) + clps_por_pagina - 1) // clps_por_pagina)


    tag_term = []

    return render_template(
        'layouts/index.html',
        clps=clps_pagina,
        page=page,
        total_paginas=total_paginas,
        valor=clps_por_pagina,
        search_term=search_term,
        tag_term=tag_term
    )