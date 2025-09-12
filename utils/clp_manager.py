import json
import os
import logging
from datetime import datetime
import ipaddress
from netaddr import EUI, NotRegisteredError
from scapy.all import sniff, srp, Ether, ARP, IP, conf
from .portas import escanear_portas  # Sua função de escaneamento de portas
from utils.root import get_project_root

# --- Configurações ---
PROJECT_ROOT = get_project_root()
CLPS_FILE = os.path.join(PROJECT_ROOT, "clps.json")

# --- Carregamento do JSON existente ---
def _carregar_clps():
    if not os.path.exists(CLPS_FILE):
        return []
    try:
        with open(CLPS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            return json.loads(content) if content else []
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Erro ao carregar clps.json: {e}")
        return []

_clps_data = _carregar_clps()


# --- Funções de salvamento ---
def salvar_clps():
    try:
        with open(CLPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(_clps_data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        logging.error(f"Erro ao salvar clps.json: {e}")


# --- Funções de busca ---
def buscar_por_ip(ip_procurado: str):
    for clp in _clps_data:
        if clp.get("ip") == ip_procurado:
            return clp
    return None


# --- Criação / Enriquecimento de dispositivo ---
def criar_dispositivo(dados, grupo="Sem Grupo"):
    ip = dados.get("ip")
    mac = dados.get("mac")
    subnet = dados.get("subnet", "Desconhecida")
    portas = dados.get("portas", [])

    # Verifica se já existe
    existente = buscar_por_ip(ip)
    if existente:
        logging.info(f"[INFO] Atualizando dispositivo existente: {ip}")
        existente["portas"] = list(set(existente.get("portas", []) + portas))
        salvar_clps()
        return existente

    # Determina fabricante
    try:
        fabricante = str(EUI(mac).oui.registration().org)
    except NotRegisteredError:
        fabricante = "Desconhecido"

    # Determina tipo pelo fabricante ou portas
    tipo = "Desconhecido"
    if fabricante.lower().startswith(("siemens", "rockwell", "schneider", "mitsubishi")):
        tipo = "CLP"
    elif 5000 in portas or 5357 in portas:
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
        "mac": mac,
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
        "portas": portas,
        "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "logs": [
            {
                "acao": "Enriquecimento",
                "detalhes": f"Dispositivo identificado como {tipo}, fabricante: {fabricante}",
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
    }

    _clps_data.append(dispositivo)
    salvar_clps()
    logging.info(f"[INFO] Novo dispositivo criado: {ip}")
    return dispositivo


# --- Descoberta passiva ---
def discover_subnets_passively(timeout=60):
    discovered_ips = set()

    def packet_handler(packet):
        if packet.haslayer(ARP):
            discovered_ips.add(packet[ARP].psrc)
        elif packet.haslayer(IP):
            discovered_ips.add(packet[IP].src)

    print(f"[*] Ouvindo passivamente por {timeout} segundos...")
    sniff(prn=packet_handler, store=0, timeout=timeout)

    subnets = set()
    for ip in discovered_ips:
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private:
                network = ipaddress.ip_network(f"{ip}/24", strict=False)
                subnets.add(str(network))
        except ValueError:
            continue

    return list(subnets)


# --- Scan ARP ativo ---
def scan_arp_on_subnet(network_range, timeout=3):
    clients_list = []
    arp_request = ARP(pdst=network_range)
    broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
    arp_request_broadcast = broadcast / arp_request
    answered_list, _ = srp(arp_request_broadcast, timeout=timeout, verbose=0)

    for _, received_packet in answered_list:
        client_info = {
            "ip": received_packet.psrc,
            "mac": received_packet.hwsrc,
            "subnet": network_range
        }
        clients_list.append(client_info)
    return clients_list


# --- Descoberta completa ---
def run_full_discovery(passive_timeout=60):
    subnets = discover_subnets_passively(passive_timeout)
    all_devices = []

    for subnet in subnets:
        clients = scan_arp_on_subnet(subnet)
        for client in clients:
            client["portas"] = escanear_portas(client["ip"])
            dispositivo = criar_dispositivo(client)
            all_devices.append(dispositivo)

    return all_devices


# --- Execução principal ---
if __name__ == "__main__":
    print("--- INICIANDO DESCOBERTA DE REDE ---")
    dispositivos = run_full_discovery(passive_timeout=60)
    print(f"[+] Total de dispositivos encontrados: {len(dispositivos)}")
    print("--- EXECUÇÃO FINALIZADA ---")
