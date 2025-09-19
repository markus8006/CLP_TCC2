# src/services/connection_service.py
from src.adapters.modbus_adapter import ModbusAdapter
from src.adapters.opcua_adapter import OpcUaAdapter

ADAPTERS = {
    "Modbus": ModbusAdapter(),
    "OPCUA": OpcUaAdapter()
}

def conectar(clp, port=None):
    adapter = ADAPTERS.get(clp["tipo"])
    if adapter:
        return adapter.conectar(clp, port)
    clp["logs"].append("Adapter não disponível")
    return False

def desconectar(clp):
    adapter = ADAPTERS.get(clp["tipo"])
    if adapter:
        adapter.desconectar(clp)
    else:
        clp["logs"].append("Adapter não disponível")
