from src.adapters.base_adapter import BaseAdapter
from typing import Any, Optional, Dict, List

class OpcUaAdapter(BaseAdapter):
    def __init__(self):
        self.client = None  # aqui entraria opcua.Client futuramente

    def connect(self, clp: Dict[str, Any], port: Optional[int] = None) -> bool:
        print(f"[OPCUAAdapter] Conectando em {clp}")
        # self.client = Client(address)
        # self.client.connect()
        raise NotImplementedError
    

    def disconnect(self, clp: Dict[str, Any]) -> None:
        print("[OPCUAAdapter] Desconectando")
        # self.client.disconnect()
        raise NotImplementedError
    


    def read_tag(self, clp: Dict[str, Any], address: int, count: int = 1) -> Optional[List[int]]:
        print(f"[OPCUAAdapter] Lendo {address}")
        # node = self.client.get_node(tag)
        # return node.get_value()
        raise NotImplementedError

    def write_tag(self, clp: Dict[str, Any], address: int, value:Any) -> bool:
        print(f"[OPCUAAdapter] Escrevendo {value} em {address}")
        # node = self.client.get_node(tag)
        # node.set_value(value)
        raise NotImplementedError

    
