from src.app import db
from src.models.Users import User, UserRole

def test_login_page(client):
    """
    Testa se a página de login é carregada corretamente.
    """
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data

def test_successful_login_and_logout(client, new_user):
    """
    Testa um ciclo completo de login e logout com sucesso.
    """
    with client.application.app_context():
        db.session.add(new_user)
        db.session.commit()

    # Tenta fazer login
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # Verifica se foi redirecionado para a página principal
    assert b'CLPs Detectados' in response.data 
    # Verifica a mensagem de boas-vindas

    # Tenta fazer logout
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Sess\xc3\xa3o encerrada.' in response.data
    # Verifica se voltou para a página de login
    assert b'Login' in response.data

def test_login_with_invalid_credentials(client, new_user):
    """
    Testa a falha de login com uma senha incorreta.
    """
    with client.application.app_context():
        db.session.add(new_user)
        db.session.commit()

    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Utilizador ou senha inv\xc3\xa1lidos.' in response.data
    assert b'CLPs Detectados' not in response.data

def test_register_first_user_as_admin(client):
    """
    Testa o registo do primeiro utilizador, que deve ser automaticamente definido como ADMIN.
    """
    # Garante que não há utilizadores na base de dados
    with client.application.app_context():
        User.query.delete()
        db.session.commit()

    response = client.post('/register', data={
        'username': 'firstadmin',
        'password': 'adminpass',
        'password2': 'adminpass',
        'user_type': 'user' # Mesmo que 'user' seja enviado, deve ser ignorado
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Primeiro utilizador (Administrador) registado com sucesso!' in response.data

    # Verifica se o utilizador foi criado como ADMIN na base de dados
    with client.application.app_context():
        user = User.query.filter_by(username='firstadmin').first()
        assert user is not None
        assert user.is_admin
        assert user.role == UserRole.ADMIN

def test_register_by_admin(client, new_admin):
    """
    Testa se um admin pode registar um novo utilizador.
    """
    with client.application.app_context():
        db.session.add(new_admin)
        db.session.commit()

    # Faz login como admin
    client.post('/login', data={'username': 'adminuser', 'password': 'adminpassword'}, follow_redirects=True)

    # Admin regista um novo utilizador
    response = client.post('/register', data={
        'username': 'newuserbyadmin',
        'password': 'password123',
        'password2': 'password123',
        'user_type': 'user'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Novo utilizador registado com sucesso!' in response.data

    # Verifica se o novo utilizador existe na base de dados
    with client.application.app_context():
        new_user = User.query.filter_by(username='newuserbyadmin').first()
        assert new_user is not None
        assert not new_user.is_admin
        assert new_user.role == UserRole.USER

def test_register_access_denied_for_non_admin(client, new_user, new_admin):
    """
    Testa se um utilizador normal não pode aceder à página de registo quando já existem outros utilizadores.
    """
    with client.application.app_context():
        db.session.add(new_admin) # Garante que não é o primeiro utilizador
        db.session.add(new_user)
        db.session.commit()

    # Faz login como utilizador normal
    client.post('/login', data={'username': 'testuser', 'password': 'testpassword'}, follow_redirects=True)

    # Tenta aceder à página de registo
    response = client.get('/register', follow_redirects=True)
    assert response.status_code == 200
    assert b'O registo de novos utilizadores est\xc3\xa1 desabilitado.' in response.data
    # Deve ser redirecionado para o login
    assert b'Login' in response.data

def test_register_fails_for_existing_username(client):
    """
    Testa a falha de registo ao tentar usar um nome de utilizador que já existe.
    """
    # Primeiro, regista o utilizador inicial (que será admin)
    client.post('/register', data={
    'username': 'existinguser',
    'password': 'password',
    'password2': 'password',
    'user_type': 'admin'
    }, follow_redirects=True)

# Faz login como admin
    client.post('/login', data={
    'username': 'existinguser',
    'password': 'password'
    }, follow_redirects=True)

# Tenta registar novamente com o mesmo nome de utilizador
    response = client.post('/register', data={
    'username': 'existinguser',
    'password': 'anotherpassword',
    'password2': 'anotherpassword',
    'user_type': 'user'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Erro ao registar: nome de utilizador j\xc3\xa1 existe' in response.data
    
