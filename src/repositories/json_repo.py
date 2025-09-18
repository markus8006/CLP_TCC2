# src/repositories/json_repo.py
import json
import os
import tempfile
import logging
from typing import Any


def atomic_write(path: str, data: Any) -> None:
    """
    Salva dados em JSON de forma atômica:
    - Escreve em arquivo temporário
    - Substitui o arquivo original
    Evita corrupção em caso de crash ou concorrência.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    dirn = os.path.dirname(path) or "."
    with tempfile.NamedTemporaryFile("w", dir=dirn, delete=False, encoding="utf-8") as tf:
        json.dump(data, tf, indent=2, ensure_ascii=False)
        tmpname = tf.name
    os.replace(tmpname, path)


def carregar_arquivo(path: str, default: Any = None) -> Any:
    """
    Carrega um JSON do disco.
    Retorna default (lista/dict) se o arquivo não existir ou estiver inválido.
    """
    if not os.path.exists(path):
        return default if default is not None else []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            return json.loads(content) if content.strip() else (default or [])
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Erro ao carregar {path}: {e}")
        return default if default is not None else []


def salvar_arquivo(path: str, data: Any) -> None:
    """
    Salva um JSON de forma segura.
    """
    try:
        atomic_write(path, data)
    except IOError as e:
        logging.error(f"Erro ao salvar {path}: {e}")
