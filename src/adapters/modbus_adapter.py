# src/adapters/modbus_adapter.py
from typing import Dict, Any, Optional, List, cast
from pymodbus.client import ModbusTcpClient

from src.adapters.base_adapter import BaseAdapter
from src.utils.log.log import setup_logger

logger = setup_logger()


class ModbusAdapter(BaseAdapter):
    """
    Adapter simples para Modbus TCP usando pymodbus (API síncrona).
    """

    def __init__(self) -> None:
        # mapa ip -> ModbusTcpClient
        self._active_clients: Dict[str, ModbusTcpClient] = {}

    def connect(self, clp: Dict[str, Any], port: Optional[int] = None) -> bool:
        ip = clp.get("ip")
        if not ip:
            logger.error({"evento": "connect: ip ausente em clp", "clp": clp})
            return False

        p = port or (clp.get("portas") or [502])[0]
        try:
            client = ModbusTcpClient(host=ip, port=p)
            ok = client.connect()
        except Exception as e:
            logger.error({"evento": "Erro ao criar/conectar ModbusTcpClient", "ip": ip, "porta": p, "detalhes": str(e)})
            ok = False
            client = None

        clp.setdefault("logs", [])
        if ok and client:
            self._active_clients[ip] = client
            clp["status"] = "Conectado"
            clp["logs"].append(f"Conectado via Modbus na porta {p}")
            logger.info({"evento": "Modbus conectado", "ip": ip, "porta": p})
            return True
        else:
            clp["status"] = "Offline"
            clp["logs"].append(f"Falha ao conectar via Modbus na porta {p}")
            logger.warning({"evento": "Falha na conexão Modbus", "ip": ip, "porta": p})
            return False





    def disconnect(self, clp: Dict[str, Any]) -> None:
        ip = clp.get("ip")
        if not ip:
            logger.error({"evento": "disconnect: ip ausente em clp", "clp": clp})
            return

        clp.setdefault("logs", [])
        client = self._active_clients.pop(ip, None)
        if not client:
            clp["logs"].append(f"Tentativa de desconectar um IP não conectado: {ip}")
            logger.warning({"evento": "disconnect: ip não conectado", "ip": ip})
            return

        try:
            client.close()
        except Exception as e:
            logger.error({"evento": "Erro ao fechar cliente Modbus", "ip": ip, "detalhes": str(e)})

        clp["status"] = "Offline"
        clp["logs"].append("Desconectado do Modbus")
        logger.info({"evento": "Desconectado Modbus", "ip": ip})




    def read_tag(self, clp: Dict[str, Any], address: int, count: int = 1) -> Optional[List[int]]:
        """
        Lê registradores via read_holding_registers. Retorna lista de ints ou None.
        Implementa chamada adaptativa para cobrir variações de API/stubs e evita alerta do Pylance.
        """
        ip = clp.get("ip")
        if not ip:
            logger.error({"evento": "read_tag: ip ausente em clp", "clp": clp})
            return None

        client = self._active_clients.get(ip)
        if not client:
            logger.warning({"evento": "read_tag: cliente Modbus não conectado", "ip": ip})
            return None

        client_any = cast(Any, client)

        # tenta chamada posicional primeiro; se TypeError (assinatura diferente), tenta com keywords
        try:
            # type: ignore[call-arg]  # suprime o aviso do Pylance sobre argumentos posicional/nominal
            response = client_any.read_holding_registers(address, count)
        except TypeError:
            try:
                # tente com keywords explicitamente (muitos stubs/versões aceitam esse formato)
                response = client_any.read_holding_registers(address=address, count=count, unit=clp.get("unit", 1))
            except Exception as e:
                logger.error({"evento": "read_tag: erro ao chamar read_holding_registers (fallback)", "ip": ip, "detalhes": str(e)})
                return None
        except Exception as e:
            logger.error({"evento": "read_tag: erro inesperado na chamada", "ip": ip, "detalhes": str(e)})
            return None

        if not response:
            logger.warning({"evento": "read_tag: resposta vazia", "ip": ip, "address": address})
            return None

        # Checa se resposta é erro (se suportado)
        try:
            if hasattr(response, "isError") and response.isError():
                logger.warning({"evento": "read_tag: resposta indica erro do dispositivo", "ip": ip, "address": address})
                return None
        except Exception:
            # ignore introspection errors
            pass

        registers = getattr(response, "registers", None)
        if registers is None:
            logger.warning({"evento": "read_tag: resposta sem atributo 'registers'", "ip": ip, "address": address})
            return None

        try:
            return list(registers)
        except Exception as e:
            logger.error({"evento": "read_tag: falha ao converter registers", "ip": ip, "detalhes": str(e)})
            return None




    def write_tag(self, clp: Dict[str, Any], address: int, value:Any) -> bool:
        """
        Escreve um registrador e retorna True se sucesso.
        """
        ip = clp.get("ip")
        if not ip:
            logger.error({"evento": "write_tag: ip ausente em clp", "clp": clp})
            return False

        client = self._active_clients.get(ip)
        if not client:
            logger.warning({"evento": "write_tag: cliente Modbus não conectado", "ip": ip})
            return False

        try:
            result = client.write_register(address, value)
        except Exception as e:
            logger.error({"evento": "write_tag: erro ao escrever registrador", "ip": ip, "address": address, "detalhes": str(e)})
            return False

        # se result tiver isError, verifique
        try:
            if hasattr(result, "isError") and result.isError():
                logger.warning({"evento": "write_tag: resposta de erro ao escrever", "ip": ip, "address": address})
                return False
        except Exception:
            pass

        logger.info({"evento": "write_tag: escrito registrador", "ip": ip, "address": address, "valor": value})
        return True
