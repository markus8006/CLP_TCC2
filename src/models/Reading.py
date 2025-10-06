from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.db import db

class Reading(db.Model):
    __tablename__ = 'readings'
    
    id = Column(Integer, primary_key=True)
    register_id = Column(Integer, ForeignKey('registers.id'), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    raw_value = Column(Float, nullable=False)  # Valor bruto do CLP
    scaled_value = Column(Float, nullable=False)  # Valor após escala/offset
    quality = Column(String(20), default='good')  # good, bad, uncertain
    
    # Relacionamentos
    register = relationship("Register", back_populates="readings")
    
    # Índices para performance em consultas time-series
    __table_args__ = (
        Index('idx_readings_register_timestamp', 'register_id', 'timestamp'),
        Index('idx_readings_timestamp', 'timestamp'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'register_id': self.register_id,
            'timestamp': self.timestamp.isoformat(),
            'raw_value': self.raw_value,
            'scaled_value': self.scaled_value,
            'quality': self.quality
        }
