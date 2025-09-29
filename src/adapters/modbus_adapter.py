# src/adapters/modbus_adapter.py
from typing import Dict, Any, Optional, List
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
            for keys, values in self._active_clients.items():
                if ip == keys:
                    client = self._active_clients[keys]
                    ok = True
                    break
            else:
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
        """
        ip = clp.get("ip")
        if not ip:
            logger.error({"evento": "read_tag: ip inválido ou ausente", "clp": clp})
            return None

        client = self._active_clients.get(ip)
        if not client:
            logger.warning({"evento": "read_tag: cliente Modbus não conectado", "ip": ip})
            return None

        # A sua biblioteca usa 'device_id'. O padrão é 1.
        device_id = clp.get("unit", 1)
        device_id = 2
        count = 3

        try:
            # --- CORREÇÃO FINAL APLICADA ---
            # A chamada agora usa o parâmetro 'device_id', conforme a assinatura
            # da sua biblioteca.
            response = client.read_holding_registers(address, count=count, device_id=device_id)

            if not response or response.isError():
                logger.warning({
                    "evento": "read_tag: resposta de erro do Modbus",
                    "ip": ip, 'id' : device_id, "address": address, "response": str(response)
                })
                return None
            
            return response.registers

        except Exception as e:
            logger.error({
                "evento": "read_tag: exceção durante a leitura",
                "ip": ip, "detalhes": str(e)
            })
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
