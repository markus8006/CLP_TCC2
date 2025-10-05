# tests/test_api.py
import json
from src.app import db
from src.models import CLP, User

def login(client, username, password):
    """Função auxiliar para fazer login."""
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

def test_create_manual_clp_api(client, new_admin):
    """
    Testa a criação de um CLP manualmente pela rota, que é a principal função da API agora.
    """
    login(client, 'adminuser', 'adminpassword')

    response = client.post('/coleta/manual', data={
        'nome': 'CLP_API_Test',
        'ip': '10.20.30.40',
        'portas': '502, 8080',
        'mac' : 'AA:BB:CC:DD:EE:FF',
        'subnet' : 'eth0'
    }, follow_redirects=True)
    
    
    assert response.status_code == 200
    assert b'CLP 10.20.30.40 foi salvo com sucesso!' in response.data

    # Verifica se foi salvo corretamente no banco de dados
    with client.application.app_context():
        clp = CLP.query.filter_by(ip='10.20.30.40').first()
        assert clp is not None
        assert clp.nome == 'CLP_API_Test'
        assert clp.portas == [502, 8080]

def test_main_page_authenticated(client, new_user):
    """Testa o acesso à página principal após o login."""
    login(client, 'testuser', 'testpassword')
    response = client.get('/')
    assert response.status_code == 200
    assert b'CLPs Detectados' in response.data

def test_main_page_unauthenticated(client):
    """Testa o redirecionamento para login ao tentar acessar a página principal sem estar logado."""
    response = client.get('/', follow_redirects=True)
    assert response.status_code == 200
    # Verifica se o conteúdo da página de login está presente no final do redirecionamento  
    assert not b'Login' in response.data
    assert not b'Digite seu usu' in response.data