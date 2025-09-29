# src/utils/ymal/create_plc_registers.py
import os
import yaml
from typing import List, Dict, Any

# não executar ClpController.listar() no import; importe dentro da função
def create_plc_registers_file(output_path: str | None = None) -> str:
    """
    Cria src/data/plc_registers.yaml com registradores exemplo para cada CLP cadastrado.
    Retorna o caminho do arquivo criado.
    """
    if output_path is None:
        output_path = os.path.join("src", "data", "plc_registers.yaml")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # importa aqui para garantir app context se for necessário no caller
    try:
        from src.controllers.clp_controller import ClpController
        clps = ClpController.listar() or []
    except Exception:
        # fallback: criar vazio se não for possível carregar CLPs (ex.: fora do app context)
        clps = []

    plc_registers: Dict[str, List[Dict[str, Any]]] = {}
    for clp in clps:
        ip = clp.get("ip")
        if not ip:
            continue
        plc_registers[ip] = [
            {"address": 0, "name": "Registrador_0"},
            {"address": 1, "name": "Registrador_1"}
        ]

    # se não houver CLPs, deixar um exemplo para localhost
    if not plc_registers:
        plc_registers["127.0.0.1"] = [
            {"address": 0, "name": "Registrador_0"},
            {"address": 1, "name": "Registrador_1"}
        ]

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(plc_registers, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return output_path

if __name__ == "__main__":
    # Uso CLI (executar manualmente)
    path = create_plc_registers_file()
    print("Arquivo criado:", path)
