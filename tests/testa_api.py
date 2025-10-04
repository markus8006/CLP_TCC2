# tests/test_api_routes.py

import json
from src.app import db
from src.models import CLP, User, UserRole

# --- Funções de Ajuda ---

def login(client, username, password):
    """Função auxiliar para fazer login e retornar o cliente autenticado."""
    client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)
    return client

# --- Testes para as Rotas da API ---

def test_get_clps_unauthenticated(client):
    """
    Testa se o acesso à lista de CLPs é negado sem autenticação.
    """
    response = client.get('/clp/')
    # Espera-se um redirecionamento para a página de login (status 302)
    assert response.status_code == 302 

def test_get_clps_authenticated(client, new_user):
    """
    Testa a listagem de CLPs via API quando o usuário está autenticado.
    """
    with client.application.app_context():
        db.session.add(new_user)
        db.session.commit()
    
    client = login(client, 'testuser', 'testpassword')

    response = client.get('/clp/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert isinstance(data['clps'], list)

def test_get_clp_by_ip(client, new_user):
    """
    Testa a busca de um CLP específico por IP.
    """
    with client.application.app_context():
        db.session.add(new_user)
        # Adiciona um CLP para o teste
        clp = CLP(nome='CLP_Test_API', ip='192.168.3.100', porta=502)
        db.session.add(clp)
        db.session.commit()

    client = login(client, 'testuser', 'testpassword')
    
    # Testa buscando um CLP existente
    response = client.get('/clp/192.168.3.100')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['clp']['nome'] == 'CLP_Test_API'

    # Testa buscando um CLP que não existe
    response = client.get('/clp/192.168.3.101')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'CLP não encontrado' in data['message']

def test_rename_clp(client, new_admin):
    """
    Testa a funcionalidade de renomear um CLP (requer admin).
    """
    with client.application.app_context():
        db.session.add(new_admin)
        clp = CLP(nome='CLP_To_Rename', ip='192.168.4.100')
        db.session.add(clp)
        db.session.commit()

    client = login(client, 'adminuser', 'adminpassword')

    response = client.post('/clp/192.168.4.100/rename', 
                           data=json.dumps({'novo_nome': 'CLP_Renamed'}),
                           content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True

    # Verifica se o nome foi realmente alterado no banco
    with client.application.app_context():
        updated_clp = CLP.query.filter_by(ip='192.168.4.100').first()
        assert updated_clp.nome == 'CLP_Renamed'

def test_add_and_remove_tag(client, new_admin):
    """
    Testa adicionar e remover uma tag de um CLP (requer admin).
    """
    with client.application.app_context():
        db.session.add(new_admin)
        clp = CLP(nome='CLP_With_Tags', ip='192.168.5.100', metadata={})
        db.session.add(clp)
        db.session.commit()

    client = login(client, 'adminuser', 'adminpassword')
    
    # Adicionar tag
    response_add = client.post('/clp/192.168.5.100/tags', 
                               data=json.dumps({'tag': 'Linha-A'}),
                               content_type='application/json')
    assert response_add.status_code == 200
    data_add = json.loads(response_add.data)
    assert 'Linha-A' in data_add['tags']

    # Remover tag
    response_remove = client.delete('/clp/192.168.5.100/tags/Linha-A')
    assert response_remove.status_code == 200
    data_remove = json.loads(response_remove.data)
    assert 'Linha-A' not in data_remove['tags']

def test_get_clp_values(client, new_user):
    """
    Testa a rota que retorna os valores e logs de um CLP.
    """
    with client.application.app_context():
        db.session.add(new_user)
        clp = CLP(nome='CLP_Values', ip='192.168.6.100', status='Online')
        db.session.add(clp)
        db.session.commit()
    
    client = login(client, 'testuser', 'testpassword')

    response = client.get('/192.168.6.100/values')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'registers_values' in data
    assert 'logs' in data
    assert data['status'] == 'Online'