# src/controllers/clp_controller.py
from src.services.clp_service import criar_clp, buscar_clp_por_ip, buscar_todos_clps
from src.services.connection_service import conectar as conectar_service, desconectar as desconectar_service
from typing import List, Dict, Any

class ClpController:
    """
    Controller usado pelas views / blueprints.
    Exponha aqui métodos fáceis de usar.
    """
    @staticmethod
    def listar() ->  List[Dict[str, Any]]:
        return buscar_todos_clps()

    @staticmethod
    def obter_por_ip(ip: str):
        return buscar_clp_por_ip(ip)

    @staticmethod
    def criar(dados: Dict[str, str|List[Any]]):
        return criar_clp(dados)
    
    @staticmethod
    def editar_clp(clp : Dict[str, str|List[Any]], new_clp : Dict[str, str|List[Any]]):
        criar_clp(clp, new_clp)


    @staticmethod
    def conectar(ip: str, port: int = None):
        clp = buscar_clp_por_ip(ip)
        if not clp:
            return False
        return conectar_service(clp, port=port)

    @staticmethod
    def desconectar(ip: str):
        clp = buscar_clp_por_ip(ip)
        if not clp:
            return False
        desconectar_service(clp)
        return True
