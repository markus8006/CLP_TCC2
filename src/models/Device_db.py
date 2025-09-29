from src.views import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON

class DeviceDB(db.Model):
    __tablename__ = "devices"
    ip = db.Column(db.String(50), primary_key=True)
    mac = db.Column(db.String(50))
    subnet = db.Column(db.String(50))
    nome = db.Column(db.String(100))
    tipo = db.Column(db.String(50))
    grupo = db.Column(db.String(50))
    protocolo = db.Column(db.String(50))
    metadata = db.Column(JSON)
    tags = db.Column(JSON)
    status = db.Column(db.String(50))
    portas = db.Column(JSON)
    data_registro = db.Column(db.DateTime, default=datetime.utcnow)
    logs = db.Column(JSON)
