# src/services/ui_adapter.py
from typing import Dict, List
from src.services.db_service import get_register_values

def get_registers_for_ui(clp_ip: str) -> Dict[str, List[float]]:
    """
    Retorna dicionário no mesmo formato que o JSON antigo:
    {
        "temp1": [val1, val2, ...],
        "temp2": [val1, val2, ...]
    }
    """
    raw = get_register_values(clp_ip)
    result: Dict[str, List[float]] = {}

    for name, entries in raw.items():
        # converte todos os valores para float (ou int se preferir)
        result[name] = [float(e["value"]) for e in entries]

    return result
