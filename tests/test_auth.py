# tests/test_auth.py
from src.app import db
from src.models.Users import User, UserRole

def test_login_and_logout(client, new_user):
    """Testa um ciclo de login e logout com sucesso."""
    # Tenta fazer login
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'CLPs Detectados' in response.data  # Verifica se foi para a página principal  

    # Tenta fazer logout
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Sess' in response.data # Mensagem de "Sessão encerrada"
    assert b'Login' in response.data # Verifica se voltou para a página de login

def test_register_first_user_as_admin(client):
    """Testa se o primeiro usuário registrado se torna ADMIN automaticamente."""
    # Garante que não há usuários
    with client.application.app_context():
        User.query.delete()
        db.session.commit()

    response = client.post('/register', data={
        'username': 'firstadmin',
        'password': 'adminpass',
        'password2': 'adminpass',
        'user_type': 'user' # Ignorado, deve ser admin
    }, follow_redirects=True)

    assert b'Primeiro utilizador (Administrador) registado com sucesso!' in response.data

    with client.application.app_context():
        user = User.query.filter_by(username='firstadmin').first()
        assert user is not None
        assert user.is_admin

def test_register_access_denied_for_non_admin(client, new_user, new_admin):
    """
    Testa se um usuário comum não pode acessar a página de registro se já existem usuários.
    """
    # Faz login como usuário comum
    client.post('/login', data={'username': 'testuser', 'password': 'testpassword'}, follow_redirects=True)

    # Tenta acessar a página de registro
    response = client.get('/register', follow_redirects=True)
    
    # Ele deve ser redirecionado para a página de login com uma mensagem de aviso
    assert b'O registo de novos utilizadores est' in response.data
    assert b'Login' in response.data