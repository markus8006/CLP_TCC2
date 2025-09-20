# src/models/device.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class Device:
    ip: str
    mac: str
    subnet: str
    portas: Optional[List[int]] = field(default_factory=list[int])
    nome: Optional[str] = None
    tipo: str = "Desconhecido"  
    protocolo : str = "Desconhecido"
    grupo: str = "Sem Grupo"
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "fabricante": "Desconhecido",
        "modelo": "Desconhecido",
        "versao_firmware": "N/A",
        "data_instalacao": None,
        "responsavel": "",
        "numero_serie": ""
    })
    tags: List[str] = field(default_factory=list[str])
    status: str = "Offline"
    data_registro: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logs: List[Dict[str, str]] = field(default_factory=list[Dict[str, str]])

    def to_dict(self) -> Dict[str, Any]:
        if self.portas == None:
            self.portas = []

        return {
            "ip": self.ip,
            "mac": self.mac or "",
            "subnet": self.subnet,
            "nome": self.nome or f"{self.tipo}_{self.ip}",
            "tipo": self.tipo,
            "grupo": self.grupo,
            "metadata": self.metadata,
            "tags": self.tags,
            "status": self.status,
            "portas": sorted(list(set(self.portas))),
            "data_registro": self.data_registro,
            "logs": self.logs
        }
