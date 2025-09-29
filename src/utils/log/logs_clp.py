# src/utils/log_utils.py
from typing import Dict, Any

def add_log(clp: Dict[str, Any], entry: str):
    """
    Adiciona uma entrada de log no CLP evitando duplicatas consecutivas
    e mantendo no máximo 200 logs.
    """
    logs = clp.setdefault("logs", [])
    if logs and logs[-1] == entry:
        return
    logs.append(entry)
    if len(logs) > 200:
        logs.pop(0)
