# tests/conftest.py

import pytest
from src.app import create_app, db
from src.models.Users import User, UserRole

@pytest.fixture(scope='module')
def app():
    """Cria e configura uma nova instância da aplicação para cada módulo de teste."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",  # Usa um banco de dados em memória para testes
        "WTF_CSRF_ENABLED": False,  # Desabilita CSRF para facilitar os testes de formulário
        "LOGIN_DISABLED": False,
    })

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope='module')
def client(app):
    """Um cliente de teste para a aplicação."""
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    """Um executor de comandos CLI para a aplicação."""
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def new_user():
    """Cria um novo usuário para os testes."""
    user = User(username='testuser', role=UserRole.USER)
    user.set_password('testpassword')
    return user

@pytest.fixture(scope='function')
def new_admin():
    """Cria um novo usuário administrador para os testes."""
    admin = User(username='adminuser', role=UserRole.ADMIN)
    admin.set_password('adminpassword')
    return admin

