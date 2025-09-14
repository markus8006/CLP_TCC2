# src/repositories/json_repo.py
import json
import os
import tempfile
import logging
from typing import List, Dict, Any

def carregar_arquivo(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            return json.loads(content) if content.strip() else []
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Erro ao carregar {path}: {e}")
        return []

def salvar_arquivo(path: str, data: List[Dict[str, Any]]) -> None:
    try:
        dirpath = os.path.dirname(path)
        os.makedirs(dirpath, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=dirpath, delete=False) as tf:
            json.dump(data, tf, indent=4, ensure_ascii=False)
            tempname = tf.name
        os.replace(tempname, path)
    except IOError as e:
        logging.error(f"Erro ao salvar {path}: {e}")
