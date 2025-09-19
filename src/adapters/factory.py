from .modbus_adapter import ModbusAdapter
from .opcua_adapter import OPCUAAdapter
from .modbus_adapter import LegacyModbusAdapter

def get_adapter(protocol: str):
    adapters = {
        "modbus": ModbusAdapter,
        "opcua": OPCUAAdapter,
        "legacy": LegacyModbusAdapter
    }
    if protocol not in adapters:
        raise ValueError(f"Protocolo {protocol} não suportado")
    return adapters[protocol]()
