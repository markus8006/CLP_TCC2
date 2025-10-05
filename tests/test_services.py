# tests/test_services.py
import pytest
from unittest.mock import patch, MagicMock
from src.app import db

from src.services.clp_service import CLPService
from src.services.polling_service import polling_service, CLPPoller
from src.models import CLP

def test_create_and_get_clp(app):
    """Testa a criação e busca de um CLP através do CLPService."""
    clp_data = {
        "nome": "CLP_Oficina",
        "ip": "192.168.1.50",
        "portas": [502, 102],
        "manual": True
    }
    with app.app_context():
        CLPService.criar_ou_atualizar_clp(clp_data)
        
        retrieved_clp = CLPService.buscar_clp_por_ip("192.168.1.50")
        assert retrieved_clp is not None
        assert retrieved_clp['nome'] == "CLP_Oficina"
        assert retrieved_clp['portas'] == [502, 102]

@patch('src.services.polling_service.ModbusAdapter')
def test_polling_service_starts_for_active_clp(MockModbusAdapter, app):
    """
    Testa se o PollingService inicia um poller para um CLP ativo.
    """
    mock_adapter_instance = MockModbusAdapter.return_value
    mock_adapter_instance.connect.return_value = True

    with app.app_context():
        # Cria um CLP de teste dentro do contexto
        clp = CLP(nome='CLP_Test_Polling', ip='192.168.10.1', ativo=True)
        db.session.add(clp)
        db.session.commit()

        polling_service.set_app(app)
        polling_service.start_all_from_db()

        assert polling_service.is_running('192.168.10.1')
        polling_service.stop_all() # Limpa para o próximo teste