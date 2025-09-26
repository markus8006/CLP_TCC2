from .modbus_adapter import ModbusAdapter
from .opcua_adapter import OpcUaAdapter
from .base_adapter import BaseAdapter
from typing import Dict, Type

def get_adapter(protocol: str) -> BaseAdapter:
    adapters : Dict[str, Type[BaseAdapter]]
    adapters = {
        "modbus": ModbusAdapter,
        "opcua": OpcUaAdapter,
    }
    if protocol not in adapters:
        raise ValueError(f"Protocolo {protocol} não suportado")
    return adapters[protocol]()
