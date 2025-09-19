from .base_adapter import BaseAdapter

class LegacyModbusAdapter(BaseAdapter):
    def connect(self, address: str, **kwargs):
        print(f"[LegacyModbusAdapter] Conectando em {address}")
        # aqui entra o seu código scapy/tcpip existente

    def read_tag(self, tag: str):
        print(f"[LegacyModbusAdapter] Lendo {tag}")
        # implementação atual

    def write_tag(self, tag: str, value):
        print(f"[LegacyModbusAdapter] Escrevendo {value} em {tag}")
        # implementação atual

    def disconnect(self):
        print("[LegacyModbusAdapter] Desconectando")
