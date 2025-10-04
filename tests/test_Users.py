# tests/test_models.py

from src.models.Users import User, UserRole
from src.models.CLP import CLP

def test_new_user(new_user):
    """
    Testa a criação de um novo usuário e a verificação da senha.
    """
    assert new_user.username == 'testuser'
    assert new_user.check_password('testpassword')
    assert not new_user.check_password('wrongpassword')
    assert new_user.role == UserRole.USER
    assert not new_user.is_admin

def test_new_admin(new_admin):
    """
    Testa a criação de um usuário administrador.
    """
    assert new_admin.username == 'adminuser'
    assert new_admin.role == UserRole.ADMIN
    assert new_admin.is_admin

def test_new_clp():
    """
    Testa a criação de um novo CLP.
    """
    clp = CLP(
        nome='CLP_Teste',
        ip='192.168.1.10',
        porta=502,
        modelo='Teste'
    )
    assert clp.nome == 'CLP_Teste'
    assert clp.ip == '192.168.1.10'
    assert clp.porta == 502
    assert clp.modelo == 'Teste'



