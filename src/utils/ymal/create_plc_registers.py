# src/data/create_plc_registers.py
import os
import yaml
from src.controllers.clp_controller import ClpController
from src.utils.root.paths import YAML_FILE

# Caminho do arquivo

# Verifica se o arquivo já existe
if os.path.exists(YAML_FILE):
    print(f"{YAML_FILE} já existe. Nenhuma alteração feita.")
else:
    # Obter todos os CLPs cadastrados
    clps = ClpController.listar()
    
    plc_registers = {}
    for clp in clps:
        ip = clp.get("ip")
        if not ip:
            continue
        # Exemplo: cria dois registradores de teste por CLP
        plc_registers[ip] = [
            {"address": 0, "name": "Registrador_0"},
            {"address": 1, "name": "Registrador_1"}
        ]

    # Salva o YAML
    with open(YAML_FILE, "w") as f:
        yaml.safe_dump(plc_registers, f, default_flow_style=False)

    print(f"Arquivo criado com sucesso: {YAML_FILE}")
