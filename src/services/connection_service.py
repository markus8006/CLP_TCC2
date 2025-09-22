# src/services/connection_service.py
from src.adapters.modbus_adapter import ModbusAdapter
from src.adapters.opcua_adapter import OpcUaAdapter
# src/services/connection_service.py
from pymodbus.client import ModbusTcpClient
from typing import Optional, Dict, Any, List
from datetime import datetime


_active_clients: Dict[str, ModbusTcpClient] = {}


ADAPTERS : Dict[str, object]
ADAPTERS = { # type: ignore
    "Modbus": ModbusAdapter(),
    "OPCUA": OpcUaAdapter()
}

def conectar(clp : Dict[str|List[Any], Any], port: int|None =None):
    adapter = ADAPTERS.get(clp["tipo"])
    if adapter:
        return adapter.conectar(clp, port)
    clp["logs"].append("Adapter não disponível")
    return False

def desconectar(clp : Dict[str|list[Any], Any]):
    adapter = ADAPTERS.get(clp["tipo"])
    if adapter:
        adapter.desconectar(clp)
    else:
        clp["logs"].append("Adapter não disponível")




def get_client(ip: str) -> Optional[ModbusTcpClient]:
    return _active_clients.get(ip)

# função de log reutilizável (pode estar também em outro módulo util)
def adicionar_log(clp: Dict[str, List[Any]|Any], texto: str) -> None:
    if "logs" not in clp:
        clp["logs"] = []
    
    clp["logs"].append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {texto}")