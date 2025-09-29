from src.views import db
from datetime import datetime
from sqlalchemy.dialects.sqlite import JSON 

class CLP(db.Model):
    __tablename__ = "clps"
    
    # Colunas existentes
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(100))
    status = db.Column(db.String(50), default="Offline")

    # Novas colunas para corresponder à dataclass Device
    mac = db.Column(db.String(50))
    subnet = db.Column(db.String(50))
    tipo = db.Column(db.String(50), default="Desconhecido")
    protocolo = db.Column(db.String(50), default="Desconhecido")
    grupo = db.Column(db.String(50), default="Sem Grupo")
    data_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Campos que armazenam dados complexos (listas/dicionários)
    portas = db.Column(JSON, default=lambda: [])
    # O campo 'metadata' foi renomeado para 'device_metadata'
    device_metadata = db.Column(JSON, default=lambda: {})
    tags = db.Column(JSON, default=lambda: [])

    # Relacionamentos existentes
    registers_values = db.relationship(
        "RegisterValue",
        primaryjoin="CLP.ip == RegisterValue.clp_ip",
        backref="clp",
        lazy=True,
        cascade="all, delete-orphan"
    )

    logs = db.relationship(
        "LogEntry",
        primaryjoin="CLP.ip == LogEntry.clp_ip",
        backref="clp",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        """Converte o objeto CLP em um dicionário, similar à dataclass."""
        return {
            "ip": self.ip,
            "mac": self.mac or "",
            "subnet": self.subnet,
            "nome": self.nome or f"{self.tipo}_{self.ip}",
            "tipo": self.tipo,
            "grupo": self.grupo,
            # Atualizado para usar o novo nome do atributo
            "metadata": self.device_metadata or {},
            "tags": self.tags or [],
            "status": self.status,
            "portas": sorted(list(set(self.portas or []))),
            "data_registro": self.data_registro.strftime("%Y-%m-%d %H:%M:%S") if self.data_registro else None,
            "logs": [log.log for log in self.logs] # Simplificado para uma lista de strings
        }


class RegisterValue(db.Model):
    __tablename__ = "registers_values"
    id = db.Column(db.Integer, primary_key=True)
    clp_ip = db.Column(db.String(50), db.ForeignKey("clps.ip"), nullable=False)
    reg_name = db.Column(db.String(50))
    value = db.Column(db.String(100))
    timestamp = db.Column(db.Float, default=lambda: datetime.utcnow().timestamp())


class LogEntry(db.Model):
    __tablename__ = "logs"
    id = db.Column(db.Integer, primary_key=True)
    clp_ip = db.Column(db.String(50), db.ForeignKey("clps.ip"), nullable=False)
    log = db.Column(db.String(255))
    timestamp = db.Column(db.Float, default=lambda: datetime.utcnow().timestamp())