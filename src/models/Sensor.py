# src/models/Sensor.py
from src.db import db

class Sensor(db.Model):
    __tablename__ = "sensores"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)

    leituras = db.relationship("Leitura", back_populates="sensor")
