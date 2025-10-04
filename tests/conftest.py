# tests/conftest.py
import pytest
from src.app import create_app, db

# importe aqui todos os modelos que definem tabelas
from src.models.Users import User, UserRole
from src.models.CLP import CLP
from src.models.Tag import Tag
# ... importe quaisquer outros modelos do seu projeto

@pytest.fixture(scope="function")  # function-scoped garante DB limpo por teste
def app():
    """Cria uma app limpa por teste com DB em memória."""
    config = {
        "TESTING": True,
        # Passe a URI para create_app se sua factory aceitar um dict
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": False,
        "LOGIN_DISABLED": False,
    }

    # Se a sua create_app aceita um dict: create_app(config)
    try:
        application = create_app(config)
    except TypeError:
        # fallback: cria sem args e atualiza config em seguida
        application = create_app()
        application.config.update(config)

    # cria as tabelas dentro do contexto
    with application.app_context():
        # garante que todos os modelos foram importados (veja imports acima)
        db.create_all()

    yield application

    # teardown
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """Cliente de teste isolado por teste."""
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def new_user():
    user = User(username="testuser", role=UserRole.USER)
    user.set_password("testpassword")
    return user


@pytest.fixture(scope="function")
def new_admin():
    admin = User(username="adminuser", role=UserRole.ADMIN)
    admin.set_password("adminpassword")
    return admin
