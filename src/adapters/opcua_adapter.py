from .base_adapter import BaseAdapter

class OPCUAAdapter(BaseAdapter):
    def __init__(self):
        self.client = None  # aqui entraria opcua.Client futuramente

    def connect(self, address: str, **kwargs):
        print(f"[OPCUAAdapter] Conectando em {address}")
        # self.client = Client(address)
        # self.client.connect()

    def read_tag(self, tag: str):
        print(f"[OPCUAAdapter] Lendo {tag}")
        # node = self.client.get_node(tag)
        # return node.get_value()

    def write_tag(self, tag: str, value):
        print(f"[OPCUAAdapter] Escrevendo {value} em {tag}")
        # node = self.client.get_node(tag)
        # node.set_value(value)

    def disconnect(self):
        print("[OPCUAAdapter] Desconectando")
        # self.client.disconnect()
