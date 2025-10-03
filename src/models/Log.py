# src/models/Log.py
from src.app import db
from datetime import datetime

class Leitura(db.Model):
    __tablename__ = "leituras"

    id = db.Column(db.BigInteger, primary_key=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey("sensores.id", ondelete="CASCADE"))
    valor = db.Column(db.Numeric(15,6))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
