# src/controllers/clp_controller.py
from src.services.device_service import criar_dispositivo, buscar_por_ip, listar_clps
from src.services.connection_service import conectar, desconectar

class ClpController:
    """
    Controller usado pelas views / blueprints.
    Exponha aqui métodos fáceis de usar.
    """
    @staticmethod
    def listar():
        return listar_clps()

    @staticmethod
    def obter_por_ip(ip: str):
        return buscar_por_ip(ip)

    @staticmethod
    def criar(dados: dict):
        return criar_dispositivo(dados)

    @staticmethod
    def conectar(ip: str, port: int = None):
        clp = buscar_por_ip(ip)
        if not clp:
            return False
        return conectar(clp, port=port)

    @staticmethod
    def desconectar(ip: str):
        clp = buscar_por_ip(ip)
        if not clp:
            return False
        desconectar(clp)
        return True
