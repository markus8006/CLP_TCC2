from src.db import db
from datetime import datetime



class CLP(db.Model):
    __tablename__ = "clps"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ip = db.Column(db.String(50), nullable=False)
    porta = db.Column(db.Integer, default=502)
    modelo = db.Column(db.String(50))
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)

    configs = db.relationship("CLPConfigRegistrador", back_populates="clp")

class CLPConfigRegistrador(db.Model):
    __tablename__ = "clp_config_registradores"
    id = db.Column(db.Integer, primary_key=True)
    clp_id = db.Column(db.Integer, db.ForeignKey("clps.id"), nullable=False)
    tipo = db.Column(db.String(20))  # holding, input, coil, discrete
    endereco_inicial = db.Column(db.Integer, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    intervalo_leitura = db.Column(db.Integer, nullable=False, default=1000)
    nome_variavel = db.Column(db.String(100))
    unidade = db.Column(db.String(20))
    ativo = db.Column(db.Boolean, default=True)

    clp = db.relationship("CLP", back_populates="configs")

class HistoricoLeitura(db.Model):
    __tablename__ = "historico_leituras"
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    clp_id = db.Column(db.Integer, db.ForeignKey("clps.id"), nullable=False)
    config_id = db.Column(db.Integer, db.ForeignKey("clp_config_registradores.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    valor = db.Column(db.Float, nullable=False)

    clp = db.relationship("CLP")
    config = db.relationship("CLPConfigRegistrador")
