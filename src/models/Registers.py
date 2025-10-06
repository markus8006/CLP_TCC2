from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from src.db import db

class Register(db.Model):
    __tablename__ = 'registers'
    
    id = Column(Integer, primary_key=True)
    plc_id = Column(Integer, ForeignKey('plcs.id'), nullable=False)
    name = Column(String(100), nullable=False)  # Nome descritivo
    address = Column(Integer, nullable=False)  # Endereço do registrador
    register_type = Column(String(20), nullable=False)  # holding, input, coil, discrete
    data_type = Column(String(20), default='uint16')  # uint16, int16, float32, bool
    scale_factor = Column(Float, default=1.0)  # Para conversões
    offset = Column(Float, default=0.0)
    unit = Column(String(10))  # °C, bar, rpm, etc.
    is_active = Column(Boolean, default=True)
    
    # Relacionamentos
    plc = relationship("PLC", back_populates="registers")
    readings = relationship("Reading", back_populates="register")
    
    def to_dict(self):
        return {
            'id': self.id,
            'plc_id': self.plc_id,
            'name': self.name,
            'address': self.address,
            'register_type': self.register_type,
            'data_type': self.data_type,
            'scale_factor': self.scale_factor,
            'offset': self.offset,
            'unit': self.unit,
            'is_active': self.is_active
        }
