from src.views import db
from datetime import datetime

class CLP(db.Model):
    __tablename__ = "clps"
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(100))
    status = db.Column(db.String(50))
    registers_values = db.relationship("RegisterValue", backref="clp", lazy=True)
    logs = db.relationship("LogEntry", backref="clp", lazy=True)

class RegisterValue(db.Model):
    __tablename__ = "registers_values"
    id = db.Column(db.Integer, primary_key=True)
    clp_ip = db.Column(db.String(50), db.ForeignKey("clps.ip"), nullable=False)
    reg_name = db.Column(db.String(50))
    value = db.Column(db.String(100))
    timestamp = db.Column(db.Float, default=datetime.utcnow().timestamp)

class LogEntry(db.Model):
    __tablename__ = "logs"
    id = db.Column(db.Integer, primary_key=True)
    clp_ip = db.Column(db.String(50), db.ForeignKey("clps.ip"), nullable=False)
    log = db.Column(db.String(255))
    timestamp = db.Column(db.Float, default=datetime.utcnow().timestamp)
