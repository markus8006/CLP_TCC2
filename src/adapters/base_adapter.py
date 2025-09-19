from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    """Interface para todos os protocolos de comunicação com CLPs"""

    @abstractmethod
    def connect(self, address: str, **kwargs):
        """Estabelece conexão com o CLP"""
        pass

    @abstractmethod
    def read_tag(self, tag: str):
        """Lê uma tag/registrador"""
        pass

    @abstractmethod
    def write_tag(self, tag: str, value):
        """Escreve em uma tag/registrador"""
        pass

    @abstractmethod
    def disconnect(self):
        """Fecha a conexão"""
        pass
