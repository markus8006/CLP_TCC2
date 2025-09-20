from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class BaseAdapter(ABC):
    """Interface para todos os protocolos de comunicação com CLPs"""

    @abstractmethod
    def connect(self, clp: Dict[str, Any], port : int|None) -> bool:
        """Estabelece conexão com o CLP"""
        pass

    @abstractmethod
    def disconnect(self, clp: Dict[str, Any]):
        """Fecha a conexão"""
        pass


    @abstractmethod
    def read_tag(self, clp: Dict[str, Any], address: int, count: int = 1) -> Optional[List[int]]:
        """Lê uma tag/registrador"""
        pass

    @abstractmethod
    def write_tag(self, clp: Dict[str, Any], address: int, value:Any) -> bool:
        """Escreve em uma tag/registrador"""
        pass

