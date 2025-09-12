import json
import os
import logging
from datetime import datetime
from netaddr import EUI, NotRegisteredError
from utils.root import get_project_root
from typing import List, Dict, Any, Optional, Tuple
import tempfile

# --- Configurações ---
PROJECT_ROOT = get_project_root()
CLPS_FILE = os.path.join(PROJECT_ROOT, "data/clps.json")        # arquivo original para CLPs
DEVICES_FILE = os.path.join(PROJECT_ROOT, "data/devices.json")  # arquivo separado para outros dispositivos

# Garante que a pasta exista
os.makedirs(os.path.dirname(CLPS_FILE), exist_ok=True)

# --- Carregamento dos JSONs existentes ---
def _carregar_arquivo(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            return json.loads(content) if content.strip() else []
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Erro ao carregar {path}: {e}")
        return []

_clps_data: List[Dict[str, Any]] = _carregar_arquivo(CLPS_FILE)
_others_data: List[Dict[str, Any]] = _carregar_arquivo(DEVICES_FILE)


# --- Funções de salvamento (escrita atômica) ---
def _salvar_arquivo(path: str, data: List[Dict[str, Any]]) -> None:
    try:
        dirpath = os.path.dirname(path)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=dirpath, delete=False) as tf:
            json.dump(data, tf, indent=4, ensure_ascii=False)
            tempname = tf.name
        os.replace(tempname, path)
    except IOError as e:
        logging.error(f"Erro ao salvar {path}: {e}")

def salvar_clps() -> None:
    _salvar_arquivo(CLPS_FILE, _clps_data)

def salvar_others() -> None:
    _salvar_arquivo(DEVICES_FILE, _others_data)


# --- Funções de busca ---
def buscar_por_ip(ip_procurado: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Busca por IP em ambos os arquivos.
    Retorna (entry, source) onde source é 'clp' ou 'other' ou None.
    """
    for clp in _clps_data:
        if clp.get("ip") == ip_procurado:
            return clp, "clp"
    for dev in _others_data:
        if dev.get("ip") == ip_procurado:
            return dev, "other"
    return None, None


# --- Remover por referência (auxiliar para mover entre listas) ---
def _remover_por_ip_de_lista(ip: str, lista: List[Dict[str, Any]]) -> None:
    idx = next((i for i, e in enumerate(lista) if e.get("ip") == ip), None)
    if idx is not None:
        lista.pop(idx)


# --- Criação / Enriquecimento de dispositivo ---
def criar_dispositivo(dados: Dict[str, Any], grupo: str = "Sem Grupo") -> Dict[str, Any]:
    ip = dados.get("ip")
    mac = dados.get("mac")
    subnet = dados.get("subnet", "Desconhecida")
    portas = dados.get("portas", []) or []

    if not ip:
        logging.warning("[WARN] criar_dispositivo chamado sem IP válido.")
        return {}

    # Verifica se já existe em qualquer arquivo
    existente, origem = buscar_por_ip(ip)
    if existente:
        logging.info(f"[INFO] Atualizando dispositivo existente: {ip} (origem: {origem})")
        # Mescla portas mantendo tipo inteiro (evita duplicatas)
        portas_existentes = set(existente.get("portas", []))
        portas_existentes.update(portas)
        existente["portas"] = sorted(list(portas_existentes))
        existente.setdefault("logs", []).append({
            "acao": "Atualizacao",
            "detalhes": f"Portas atualizadas: {portas}",
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        # Salva no arquivo correto
        if origem == "clp":
            salvar_clps()
        else:
            salvar_others()
        return existente

    # Determina fabricante (com tratamento caso MAC seja inválido)
    fabricante = "Desconhecido"
    if mac:
        try:
            fabricante = str(EUI(mac).oui.registration().org)
        except (NotRegisteredError, Exception):
            fabricante = "Desconhecido"

    # Determina tipo pelo fabricante ou portas
    tipo = "Desconhecido"
    fabricante_l = fabricante.lower()
    if fabricante_l.startswith(("siemens", "rockwell", "schneider", "mitsubishi")):
        tipo = "CLP"
    elif any(p in portas for p in (5000, 5357)):
        tipo = "Computador"
    elif 22 in portas:
        tipo = "Servidor ou Dispositivo IoT"
    elif 80 in portas or 443 in portas:
        tipo = "Smartphone / Tablet / Web Device"
    elif 554 in portas or 8554 in portas:
        tipo = "Câmera IP"

    nome = f"{tipo}_{ip}" if tipo != "Desconhecido" else f"Desconhecido_{ip}"

    dispositivo = {
        "ip": ip,
        "mac": mac or "",
        "subnet": subnet,
        "nome": nome,
        "tipo": tipo,
        "grupo": grupo,
        "metadata": {
            "fabricante": fabricante,
            "modelo": "Desconhecido",
            "versao_firmware": "N/A",
            "data_instalacao": None,
            "responsavel": "",
            "numero_serie": ""
        },
        "tags": [],
        "status": "Offline",
        "portas": sorted(list(set(portas))),
        "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "logs": [
            {
                "acao": "Enriquecimento",
                "detalhes": f"Dispositivo identificado como {tipo}, fabricante: {fabricante}",
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
    }

    # Decide onde armazenar: CLPs -> CLPS_FILE, outros -> DEVICES_FILE
    if tipo == "CLP":
        _clps_data.append(dispositivo)
        salvar_clps()
        logging.info(f"[INFO] Novo CLP criado e salvo em {CLPS_FILE}: {ip}")
    else:
        _others_data.append(dispositivo)
        salvar_others()
        logging.info(f"[INFO] Novo dispositivo (não-CLP) criado e salvo em {DEVICES_FILE}: {ip}")

    return dispositivo




def conectar(clp: dict, port: int = None, timeout: float = 3.0) -> bool:
    """Tenta conectar ao CLP via Modbus e atualiza o dicionário."""
    ip = clp["IP"]
    p = port or (clp["PORTAS"][0] if clp["PORTAS"] else 502)
    try:
        client = ModbusTcpClient(host=ip, port=int(p), timeout=timeout)
        ok = client.connect()
        clp["conectado"] = bool(ok)
        if ok:
            _active_clients[ip] = client
        status = 'Conectado' if ok else 'Falha ao conectar'
        adicionar_log(clp, f"{status} usando a porta {p}.")
        return clp["conectado"]
    except Exception as e:
        clp["conectado"] = False
        adicionar_log(clp, f"Exceção ao conectar na porta {p}: {e}")
        return False

def desconectar(clp: dict):
    """Desconecta do CLP."""
    ip = clp["IP"]
    client = _active_clients.get(ip)
    if client and client.is_socket_open():
        client.close()
        if ip in _active_clients:
            del _active_clients[ip]
    clp["conectado"] = False
    adicionar_log(clp, "Conexão encerrada.")

def get_client(ip: str):
    """Obtém o objeto de cliente Modbus ativo para um determinado IP."""
    return _active_clients.get(ip)

def adicionar_porta(clp: dict, porta: int):
    """Adiciona uma nova porta à lista do CLP."""
    porta = int(porta)
    if porta not in clp["PORTAS"]:
        clp["PORTAS"].append(porta)
        adicionar_log(clp, f"Porta {porta} adicionada à lista de portas conhecidas.")

def adicionar_log(clp: dict, texto: str):
    """Adiciona uma entrada de log ao CLP."""
    if "logs" not in clp:
        clp["logs"] = []
    clp["logs"].append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {texto}")

def get_info(clp: dict) -> dict:
    """Retorna um dicionário serializável com as informações do CLP."""
    # Garante que o status está atualizado
    clp["status"] = "Online" if clp.get("conectado") else "Offline"
    
    # --- CORREÇÃO APLICADA AQUI ---
    # Padroniza as chaves para corresponderem às da função 'criar_clp'
    return {
        "IP": clp.get("IP"),  # Chave corrigida de "ip" para "IP"
        "UNIDADE": clp.get("UNIDADE"),
        "PORTAS": clp.get("PORTAS", []), # Chave corrigida de "portas" para "PORTAS"
        "conectado": clp.get("conectado", False),
        "data_registro": clp.get("data_registro"),
        "nome": clp.get("nome"),
        "descricao": clp.get("descricao"),
        "logs": clp.get("logs", []),
        "status": clp.get("status"), # Adicionamos o status aqui também
        "tags": clp.get("tags", []),
    }