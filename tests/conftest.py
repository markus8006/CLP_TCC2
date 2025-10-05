# tests/conftest.py
import pytest
from src.app import create_app, db

# importe aqui todos os modelos que definem tabelas
from src.models import User, UserRole, CLP, CLPConfigRegistrador

@pytest.fixture(scope="function")
def app():
    """Cria uma app limpa por teste com DB em memória."""
    application = create_app()
    application.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": False, # Desabilita CSRF para facilitar testes de formulários
        "LOGIN_DISABLED": False,
    })

    with application.app_context():
        db.create_all()
        yield application # Disponibiliza a app para os testes
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

@pytest.fixture(scope="function")
def new_clp_with_config(app):
    """Cria um CLP com uma configuração de registrador associada."""
    with app.app_context():
        clp = CLP(
            nome='CLP_Test_Polling', 
            ip='192.168.10.1', 
            ativo=True
        )
        db.session.add(clp)
        db.session.commit()

        config = CLPConfigRegistrador(
            clp_id=clp.id,
            nome_variavel="Temperatura",
            endereco_inicial=100,
            quantidade=1,
            intervalo_leitura=1000,
            ativo=True
        )
        db.session.add(config)
        db.session.commit()
        return clp