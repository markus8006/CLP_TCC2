# src/adapters/modbus_adapter.py
from typing import Dict, Any, Optional, List, cast
from pymodbus.client import ModbusTcpClient
from src.adapters.base_adapter import BaseAdapter
from src.utils.log.log import setup_logger

logger = setup_logger()


class ModbusAdapter(BaseAdapter):
    """
    Adapter para Modbus TCP usando pymodbus (API síncrona).
    - Gerencia conexões ativas por IP.
    - Oferece leitura/escrita de registradores.
    - Garante logs consistentes em cada operação.
    """

    def __init__(self) -> None:
        # mapa ip -> ModbusTcpClient
        self._active_clients: Dict[str, ModbusTcpClient] = {}

    # -------------------------------
    # CONEXÃO
    # -------------------------------
    def connect(self, clp: Dict[str, Any], port: Optional[int] = None) -> bool:
        """
        Conecta a um CLP via Modbus TCP.
        Se já estiver conectado, substitui a conexão.
        """
        ip = clp.get("ip")
        if not isinstance(ip, str) or not ip:
            logger.error({"evento": "connect: ip inválido ou ausente", "clp": clp})
            return False

        portas = clp.get("portas") or [502]
        p = port or portas[0]

        try:
            client = ModbusTcpClient(host=ip, port=p)
            ok = client.connect()
        except Exception as e:
            logger.error({"evento": "Erro ao conectar ModbusTcpClient", "ip": ip, "porta": p, "detalhes": str(e)})
            clp.update({"status": "Offline"})
            clp.setdefault("logs", []).append(f"Falha ao conectar na porta {p}: {e}")
            return False

        clp.setdefault("logs", [])
        if ok:
            self._active_clients[ip] = client
            clp.update({"status": "Conectado"})
            clp["logs"].append(f"Conectado via Modbus na porta {p}")
            logger.info({"evento": "Modbus conectado", "ip": ip, "porta": p})
            return True
        else:
            clp.update({"status": "Offline"})
            clp["logs"].append(f"Falha ao conectar via Modbus na porta {p}")
            logger.warning({"evento": "Falha na conexão Modbus", "ip": ip, "porta": p})
            return False

    def disconnect(self, clp: Dict[str, Any]) -> None:
        """
        Desconecta o cliente Modbus associado ao CLP.
        """
        ip = clp.get("ip")
        if not isinstance(ip, str) or not ip:
            logger.error({"evento": "disconnect: ip inválido ou ausente", "clp": clp})
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

        clp.update({"status": "Offline"})
        clp["logs"].append("Desconectado do Modbus")
        logger.info({"evento": "Desconectado Modbus", "ip": ip})

    # -------------------------------
    # LEITURA
    # -------------------------------
    def read_tag(self, clp: Dict[str, Any], address: int, count: int = 1) -> Optional[List[int]]:
        """
        Lê registradores Modbus (holding registers).
        Retorna lista de inteiros ou None em caso de falha.
        """
        ip = clp.get("ip")
        if not isinstance(ip, str) or not ip:
            logger.error({"evento": "read_tag: ip inválido ou ausente", "clp": clp})
            return None

        client = self._active_clients.get(ip)
        if not client:
            logger.warning({"evento": "read_tag: cliente Modbus não conectado", "ip": ip})
            return None

        client_any = cast(Any, client)

        # Tentativas adaptativas de chamada
        try:
            response = client_any.read_holding_registers(address, count)  # type: ignore[call-arg]
        except TypeError:
            try:
                response = client_any.read_holding_registers(address=address, count=count, unit=clp.get("unit", 1))
            except Exception as e:
                logger.error({"evento": "read_tag: erro no fallback", "ip": ip, "detalhes": str(e)})
                return None
        except Exception as e:
            logger.error({"evento": "read_tag: erro inesperado", "ip": ip, "detalhes": str(e)})
            return None

        if not response:
            logger.warning({"evento": "read_tag: resposta vazia", "ip": ip, "address": address})
            return None

        if hasattr(response, "isError") and response.isError():
            logger.warning({"evento": "read_tag: resposta de erro", "ip": ip, "address": address})
            return None

        registers = getattr(response, "registers", None)
        if registers is None:
            logger.warning({"evento": "read_tag: resposta sem 'registers'", "ip": ip, "address": address})
            return None

        try:
            return list(registers)
        except Exception as e:
            logger.error({"evento": "read_tag: falha ao converter registers", "ip": ip, "detalhes": str(e)})
            return None

    # -------------------------------
    # ESCRITA
    # -------------------------------
    def write_tag(self, clp: Dict[str, Any], address: int, value: Any) -> bool:
        """
        Escreve um registrador Modbus.
        Retorna True se sucesso.
        """
        ip = clp.get("ip")
        if not isinstance(ip, str) or not ip:
            logger.error({"evento": "write_tag: ip inválido ou ausente", "clp": clp})
            return False

        client = self._active_clients.get(ip)
        if not client:
            logger.warning({"evento": "write_tag: cliente Modbus não conectado", "ip": ip})
            return False

        try:
            result = client.write_register(address, value)
        except Exception as e:
            logger.error({"evento": "write_tag: erro ao escrever", "ip": ip, "address": address, "detalhes": str(e)})
            return False

        if hasattr(result, "isError") and result.isError():
            logger.warning({"evento": "write_tag: resposta de erro", "ip": ip, "address": address})
            return False

        logger.info({"evento": "write_tag: sucesso", "ip": ip, "address": address, "valor": value})
        return True
