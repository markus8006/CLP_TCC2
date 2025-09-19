from .base_adapter import BaseAdapter

class ModbusAdapter(BaseAdapter):
    def __init__(self):
        self.client = None  # aqui entraria pymodbus.Client futuramente

    def connect(self, address: str, **kwargs):
        print(f"[ModbusAdapter] Conectando em {address}")
        # self.client = ModbusTcpClient(address)

    def read_tag(self, tag: str):
        print(f"[ModbusAdapter] Lendo {tag}")
        # return self.client.read_holding_registers(...)

    def write_tag(self, tag: str, value):
        print(f"[ModbusAdapter] Escrevendo {value} em {tag}")
        # self.client.write_register(...)

    def disconnect(self):
        print("[ModbusAdapter] Desconectando")
        # self.client.close()
