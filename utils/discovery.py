import ipaddress
import json
from scapy.all import sniff, srp, Ether, ARP, IP

def _discover_subnets_passively(timeout=60):
    """Escuta passivamente o tráfego da rede."""
    print(f"[*] Fase 1: Ouvindo passivamente o tráfego da rede por {timeout} segundos...")
    discovered_ips = set()

    def packet_handler(packet):
        if packet.haslayer(ARP):
            discovered_ips.add(packet[ARP].psrc)
        elif packet.haslayer(IP):
            discovered_ips.add(packet[IP].src)
    
    sniff(prn=packet_handler, store=0, timeout=timeout)

    if not discovered_ips:
        return []
    
    subnets = set()
    for ip in discovered_ips:
        try:
            ip_obj = ipaddress.ip_address(ip)
            if not ip_obj.is_loopback and not ip_obj.is_multicast:
                network = ipaddress.ip_network(f"{ip}/24", strict=False)
                subnets.add(str(network))
        except ValueError:
            continue
            
    print(f"\n[+] Sub-redes ativas detectadas: {list(subnets)}")
    return list(subnets)

def _scan_arp_on_subnet(network_range, timeout=3):
    """
    Executa um ARP scan e retorna uma lista de dicionários,
    cada um contendo ip, mac e a sub-rede.
    """
    print(f"[*] Fase 2: Varrendo ativamente a sub-rede {network_range}...")
    try:
        arp_request = ARP(pdst=network_range)
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        arp_request_broadcast = broadcast / arp_request
        answered_list = srp(arp_request_broadcast, timeout=timeout, verbose=False)[0]

        clients_list = []
        for element in answered_list:
            # MODIFICADO: Cria um dicionário com todos os dados
            client_info = {
                "ip": element[1].psrc,
                "mac": element[1].hwsrc,
                "subnet": network_range
            }
            clients_list.append(client_info)
        
        print(f"[+] Encontrados {len(clients_list)} dispositivos em {network_range}.")
        return clients_list
        
    except Exception as e:
        print(f"[!] Erro durante o scan em {network_range}: {e}")
        return []

# NOVA FUNÇÃO PARA SALVAR EM JSON
def save_discoveries_to_json(devices_list, filename="discovery_results.json"):
    """Salva a lista de dispositivos descobertos em um arquivo JSON."""
    try:
        # Ordena a lista de dicionários pela chave 'ip'
        sorted_list = sorted(devices_list, key=lambda x: ipaddress.ip_address(x['ip']))
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(sorted_list, f, indent=4, ensure_ascii=False)
        print(f"\n[*] Relatório de descoberta completo salvo em '{filename}'")
    except Exception as e:
        print(f"[!] Erro ao salvar o arquivo JSON: {e}")


def run_full_discovery(passive_timeout=60):
    """
    Orquestra a descoberta e retorna uma lista de dicionários
    com os dispositivos encontrados.
    """
    try:
        target_subnets = _discover_subnets_passively(timeout=passive_timeout)
        if not target_subnets:
            print("\n[!] Não foi possível descobrir sub-redes ativas.")
            return []

        print("\n" + "="*40)
        all_found_devices = {} # Usa um dicionário para garantir IPs únicos
        for subnet in target_subnets:
            found_clients_on_subnet = _scan_arp_on_subnet(subnet)
            for client in found_clients_on_subnet:
                # Usa o IP como chave para evitar duplicatas
                all_found_devices[client['ip']] = client
        
        print("\n[*] Descoberta de IPs concluída.")
        # Retorna apenas os valores (os dicionários) do nosso agregador
        return list(all_found_devices.values())

    except PermissionError:
        print("\n[ERRO FATAL] A descoberta completa precisa ser executada com privilégios de administrador/root.")
        return None
    except Exception as e:
        print(f"\n[ERRO INESPERADO NA DESCOBERTA] {e}")
        return None