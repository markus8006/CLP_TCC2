from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Device:
    ip: str
    mac: str
    subnet: str
    portas: Optional[List[int]] = field(default_factory=list)
    nome: Optional[str] = None
    tipo: str = "Desconhecido"
    grupo: str =  "Sem Grupo"
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "fabricante": "Desconhecido",
        "modelo": "Desconhecido",
        "versao_firmware": "N/A",
        "data_instalacao": None,
        "responsavel": "",
        "numero_serie": ""
    })
    tags: List[str] = field(default_factory=list)
    status: str = "Offline"
    data_registro: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logs: List[Dict[str, str]] = field(default_factory=list)


    def to_dict(self) -> Dict[str, Any]:
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

        