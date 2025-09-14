# src/services/connection_service.py
from pymodbus.client import ModbusTcpClient
from typing import Optional, Dict, Any
import logging

_active_clients: Dict[str, ModbusTcpClient] = {}

def conectar(clp: Dict[str, Any], port: int = None, timeout: float = 3.0) -> bool:
    ip = clp.get("ip") or clp.get("IP")
    portas = clp.get("portas") or clp.get("PORTAS") or []
    p = port or (portas[0] if portas else 502)
    try:
        client = ModbusTcpClient(host=ip, port=int(p), timeout=timeout)
        ok = client.connect()
        clp["conectado"] = bool(ok)
        if ok:
            _active_clients[ip] = client
        status = "Conectado" if ok else "Falha ao conectar"
        adicionar_log(clp, f"{status} usando a porta {p}.")
        return clp["conectado"]
    except Exception as e:
        clp["conectado"] = False
        adicionar_log(clp, f"Exceção ao conectar na porta {p}: {e}")
        logging.exception("Erro ao conectar Modbus")
        return False

def desconectar(clp: Dict[str, Any]) -> None:
    ip = clp.get("ip") or clp.get("IP")
    client = _active_clients.get(ip)
    if client:
        try:
            client.close()
        except Exception:
            logging.exception("Erro fechando client Modbus")
        _active_clients.pop(ip, None)
    clp["conectado"] = False
    adicionar_log(clp, "Conexão encerrada.")

def get_client(ip: str) -> Optional[ModbusTcpClient]:
    return _active_clients.get(ip)

# função de log reutilizável (pode estar também em outro módulo util)
def adicionar_log(clp: Dict[str, Any], texto: str) -> None:
    if "logs" not in clp:
        clp["logs"] = []
    from datetime import datetime
    clp["logs"].append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {texto}")
