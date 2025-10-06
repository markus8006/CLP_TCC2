from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.db import db

class PLC(db.Model):
    __tablename__ = 'plcs'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    mac = Column(String(50), default="None")
    ip_address = Column(String(15), nullable=False)
    subnet = Column(String(100), default="None")
    portas = Column(JSON, default=[502])
    tipo = Column(String(100), default="device")
    protocol = Column(String(20), default='modbus_tcp')  # modbus_tcp, modbus_rtu
    unit_id = Column(Integer, default=1)  # Slave ID
    polling_interval = Column(Integer, default=1000)  # ms
    timeout = Column(Integer, default=3000)  # ms
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)
    last_connection = Column(DateTime(timezone=True))
    manual = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamentos
    registers = relationship("Register", back_populates="plc", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'mac': self.mac,
            'ip_address': self.ip_address,
            'subnet': self.subnet,
            'tipo': self.tipo,
            'portas': self.portas,
            'protocol': self.protocol,
            'unit_id': self.unit_id,
            'polling_interval': self.polling_interval,
            'is_active': self.is_active,
            'is_online': self.is_online,
            'register_count': len(self.registers),
            'manual' : self.manual
        }
    
