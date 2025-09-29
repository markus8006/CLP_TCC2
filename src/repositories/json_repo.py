# src/repositories/json_repo.py
import json
import os
import tempfile
import logging
from typing import Any

from flask import has_app_context

# Importações necessárias para interagir com o DB (só usadas quando houver app context)
try:
    from src.views import db
    from src.models.Registers import CLP
except Exception:
    # imports adiados / falha de import não é fatal aqui — as funções checam has_app_context()
    db = None
    CLP = None

from src.utils.root.paths import CLPS_FILE, DEVICES_FILE  # Usaremos para identificar qual tabela manipular

logger = logging.getLogger(__name__)


def atomic_write(path: str, data: Any) -> None:
    """
    Salva dados em JSON de forma atômica ou atualiza o banco de dados.
    Quando path == CLPS_FILE tentamos persistir no DB — somente se houver app context.
    """
    # Se o path for o arquivo de CLPs, a lógica é de banco de dados
    if path == CLPS_FILE:
        if not has_app_context():
            logger.error("atomic_write: tentativa de salvar CLPs no DB fora do app context. Use app.app_context().")
            return

        # checagens básicas
        if not isinstance(data, list):
            logger.error("atomic_write: dados para salvar no banco de CLPs devem ser uma lista de dicionários.")
            return

        if db is None or CLP is None:
            logger.error("atomic_write: módulos de DB não disponíveis (import falhou).")
            return

        try:
            ips_in_data = {item.get('ip') for item in data if item.get('ip')}
            if not ips_in_data:
                logger.debug("atomic_write: nenhum ip válido encontrado nos dados; nada a fazer.")
                return

            clps_in_db = CLP.query.filter(CLP.ip.in_(ips_in_data)).all()
            clps_map = {clp.ip: clp for clp in clps_in_db}

            for clp_dict in data:
                ip = clp_dict.get('ip')
                if not ip:
                    continue

                clp_obj = clps_map.get(ip)
                if clp_obj:
                    for key, value in clp_dict.items():
                        if hasattr(clp_obj, key):
                            setattr(clp_obj, key, value)
                else:
                    try:
                        new_clp = CLP(**clp_dict)
                        db.session.add(new_clp)
                    except Exception as e:
                        logger.exception("atomic_write: falha ao criar novo CLP para ip %s: %s", ip, e)

            db.session.commit()
            logger.info("atomic_write: dados de CLPs salvos no banco de dados com sucesso.")
        except Exception as e:
            logger.exception("atomic_write: erro ao salvar dados de CLPs no banco: %s", e)
            try:
                db.session.rollback()
            except Exception:
                pass
        return

    # Lógica original para outros arquivos JSON (fallback)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    dirn = os.path.dirname(path) or "."
    try:
        with tempfile.NamedTemporaryFile("w", dir=dirn, delete=False, encoding="utf-8") as tf:
            json.dump(data, tf, indent=2, ensure_ascii=False)
            tmpname = tf.name
        os.replace(tmpname, path)
    except Exception as e:
        logger.exception("atomic_write: erro na escrita atômica do arquivo %s: %s", path, e)


def carregar_arquivo(path: str, default: Any = None) -> Any:
    """
    Carrega um JSON do disco ou os dados da tabela de CLPs.
    Retorna default se o arquivo não existir ou a tabela estiver vazia.
    """
    # Se o path for o arquivo de CLPs, a lógica é de banco de dados
    if path == CLPS_FILE:
        if not has_app_context():
            logger.error("carregar_arquivo: tentativa de ler CLPs do DB fora do app context. Use app.app_context().")
            return default if default is not None else []

        if CLP is None:
            logger.error("carregar_arquivo: modelo CLP não disponível (import falhou).")
            return default if default is not None else []

        try:
            clps = CLP.query.all()
            return [clp.to_dict() for clp in clps]
        except Exception as e:
            logger.exception("carregar_arquivo: erro ao carregar CLPs do banco de dados: %s", e)
            return default if default is not None else []

    # Lógica original para outros arquivos JSON (fallback)
    if not os.path.exists(path):
        return default if default is not None else []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            return json.loads(content) if content.strip() else (default or [])
    except (json.JSONDecodeError, IOError) as e:
        logger.exception("carregar_arquivo: erro ao carregar %s: %s", path, e)
        return default if default is not None else []


def salvar_arquivo(path: str, data: Any) -> None:
    """
    Salva um JSON ou dados no banco de forma segura.
    """
    try:
        atomic_write(path, data)
    except Exception as e:
        logger.exception("salvar_arquivo: erro ao salvar em %s: %s", path, e)
