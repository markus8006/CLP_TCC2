import json
import os
from datetime import datetime
import logging

import json
import os
from datetime import datetime
from utils.root import get_project_root
import logging



# Define a raiz do projeto usando a função
PROJECT_ROOT = get_project_root()
# Define o caminho para o "banco de dados" usando a raiz correta
CLPS_FILE = os.path.join(PROJECT_ROOT, 'clps.json')

# --- O RESTO DO SEU CÓDIGO PERMANECE O MESMO ---
def _carregar_clps():
    """Função interna para ler o arquivo clps.json."""
    if not os.path.exists(CLPS_FILE):
        return [] # Retorna lista vazia se o arquivo não existe
    try:
        with open(CLPS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Erro ao carregar clps.json: {e}")
        return []

# Carrega os dados uma vez quando o módulo é importado, agindo como um cache
_clps_data = _carregar_clps()


# --- Funções Públicas (para serem usadas pelo resto do projeto) ---

def salvar_clps():
    """Salva a lista de CLPs atual (em memória) de volta para o arquivo JSON."""
    try:
        with open(CLPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(_clps_data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        logging.error(f"Erro ao salvar clps.json: {e}")

def buscar_todos():
    """Retorna a lista completa de todos os CLPs."""
    _clps_data = _carregar_clps()
    return _clps_data

def buscar_por_ip(ip_procurado):
    """Busca um CLP específico pelo seu endereço IP."""
    for clp in _clps_data:
        if clp.get('ip') == ip_procurado:
            return clp
    return None

def criar_clp(dados, grupo="Sem Grupo"):
    """
    Cria um novo dicionário de CLP com a estrutura de dados completa e o adiciona
    à lista principal.
    """

    ip = dados["ip"]
    mac = dados["mac"]
    subnet = dados["subnet"]
    # Verifica se o CLP já existe para não duplicar
    if buscar_por_ip(ip):
        logging.warning(f"Tentativa de criar um CLP que já existe: {ip}")
        return None

    # O novo modelo de dados completo
    novo_clp = {
        "ip": ip,
        "mac": mac,
        "subnet": subnet,
        "nome": f"CLP_{ip.replace('.', '_')}", # Nome padrão
        "grupo": grupo,
        "metadata": {
            "fabricante": "Desconhecido",
            "modelo": "Desconhecido",
            "versao_firmware": "N/A",
            "data_instalacao": None,
            "responsavel": "",
            "numero_serie": ""
        },
        "tags": [],
        "status": "Offline",
        "portas": [],
        "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "logs": []
    }
    
    _clps_data.append(novo_clp)
    salvar_clps() # Salva a lista atualizada no arquivo
    
    logging.info(f"Novo CLP criado e salvo: {ip} no grupo {grupo}")
    return novo_clp


def criar_clp(ip):
    buscar_por_ip

