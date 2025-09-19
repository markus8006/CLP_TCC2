# src/adapters/modbus_adapter.py
from pymodbus.client import ModbusTcpClient
from src.adapters.base_adapter import BaseAdapter
from typing import Dict, Any

_active_clients = {}

class ModbusAdapter(BaseAdapter):


    def connect(self, clp: Dict[str, Any], port: int = None) -> bool:
        ip = clp["ip"]
        p = port or (clp.get("portas") or [502])[0]
        client = ModbusTcpClient(host=ip, port=p)
        ok = client.connect()
        if ok: _active_clients[ip] = client
        clp["status"] = "Conectado" if ok else "Offline"
        clp["logs"].append(f"Conectado via Modbus na porta {p}")
        return ok

    def disconnect(self, clp: Dict[str, Any]) -> None:
        ip = clp["ip"]
        client = _active_clients.get(ip)
        if client:
            client.close()
            _active_clients.pop(ip)
        clp["status"] = "Offline"
        clp["logs"].append("Desconectado Modbus")

    def read_tag(self, clp: Dict[str, Any], address: int, count: int = 1):
        client = _active_clients.get(clp["ip"])
        if client:
            return client.read_holding_registers(address, count).registers
        return None

    def write_tag(self, clp: Dict[str, Any], address: int, value):
        client = _active_clients.get(clp["ip"])
        if client:
            client.write_register(address, value)
