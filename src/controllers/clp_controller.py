# src/controllers/clp_controller.py
from src.services.device_service import criar_dispositivo, buscar_por_ip, listar_clps, atualizar_clp
from src.services.connection_service import conectar as conectar_service, desconectar as desconectar_service

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
    def editar_clp(clp, new_clp):
        atualizar_clp(clp, new_clp)


    @staticmethod
    def conectar(ip: str, port: int = None):
        clp = buscar_por_ip(ip)
        if not clp:
            return False
        return conectar_service(clp, port=port)

    @staticmethod
    def desconectar(ip: str):
        clp = buscar_por_ip(ip)
        if not clp:
            return False
        desconectar_service(clp)
        return True
