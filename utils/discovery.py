import ipaddress
import json
from scapy.all import sniff, srp, Ether, ARP, IP, conf
from .portas import escanear_portas

# [DEBUG] Aumenta o nível de verbosidade do Scapy para nos dar mais informações se necessário
# conf.verb = 1 

def _discover_subnets_passively(timeout=60):
    """Escuta passivamente o tráfego da rede."""
    print(f"[*] Fase 1: Ouvindo passivamente o tráfego da rede por {timeout} segundos...")
    discovered_ips = set()

    def packet_handler(packet):
        if packet.haslayer(ARP):
            ip_src = packet[ARP].psrc
            # [DEBUG] Informa qual IP foi visto em um pacote ARP
            print(f"    [DEBUG] ARP visto do IP: {ip_src}")
            discovered_ips.add(ip_src)
        elif packet.haslayer(IP):
            ip_src = packet[IP].src
            # [DEBUG] Informa qual IP foi visto em um pacote IP
            print(f"    [DEBUG] Pacote IP visto do IP: {ip_src}")
            discovered_ips.add(ip_src)
    
    sniff(prn=packet_handler, store=0, timeout=timeout)

    # [DEBUG] Mostra todos os IPs únicos que foram capturados antes de processá-los
    print(f"\n[DEBUG] Total de {len(discovered_ips)} IPs únicos capturados passivamente: {list(discovered_ips)}")

    if not discovered_ips:
        return []
    
    subnets = set()
    print("[DEBUG] Processando IPs para determinar sub-redes (/24)...")
    for ip in discovered_ips:
        try:
            ip_obj = ipaddress.ip_address(ip)
            if not ip_obj.is_loopback and not ip_obj.is_multicast and not ip_obj.is_private:
                # [DEBUG] Informa sobre IPs públicos ou incomuns que foram ignorados (ajuste se necessário)
                print(f"    [DEBUG] Ignorando IP não privado/loopback/multicast: {ip}")
                continue
                
            network = ipaddress.ip_network(f"{ip}/24", strict=False)
            # [DEBUG] Mostra como cada IP foi mapeado para uma sub-rede
            print(f"    [DEBUG] IP '{ip}' mapeado para a sub-rede '{network}'")
            subnets.add(str(network))
        except ValueError:
            # [DEBUG] Informa se algum valor capturado não é um IP válido
            print(f"    [DEBUG] Valor inválido '{ip}' ignorado.")
            continue
            
    print(f"\n[+] Sub-redes ativas detectadas: {list(subnets)}")
    return list(subnets)

def _scan_arp_on_subnet(network_range, timeout=3):
    """
    Executa um ARP scan e retorna uma lista de dicionários,
    cada um contendo ip, mac e a sub-rede.
    """
    print(f"\n[*] Fase 2: Varrendo ativamente a sub-rede {network_range}...")
    clients_list = []
    try:
        # [DEBUG] Mostra o pacote exato que será enviado à rede
        arp_request = ARP(pdst=network_range)
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        arp_request_broadcast = broadcast / arp_request
        print(f"    [DEBUG] Enviando pacote ARP para a sub-rede: {network_range}")
        
        answered_list, unanswered_list = srp(arp_request_broadcast, timeout=timeout, verbose=0)

        # [DEBUG] Informa quantos pacotes receberam resposta e quantos não
        print(f"    [DEBUG] Recebidas {len(answered_list)} respostas e {len(unanswered_list)} não respostas.")

        if not answered_list:
            print(f"[!] Nenhum dispositivo respondeu na sub-rede {network_range}.")
            return []

        for sent_packet, received_packet in answered_list:
            client_info = {
                "ip": received_packet.psrc,
                "mac": received_packet.hwsrc,
                "subnet": network_range
            }
            # [DEBUG] Mostra cada dispositivo encontrado em tempo real
            print(f"    [DEBUG] Encontrado: IP={client_info['ip']}, MAC={client_info['mac']}")
            clients_list.append(client_info)
        
        print(f"[+] Encontrados {len(clients_list)} dispositivos em {network_range}.")
        return clients_list
        
    except Exception as e:
        print(f"[!] Erro durante o scan em {network_range}: {e}")
        return []

def save_discoveries_to_json(devices_list, filename="data/discovery_results.json"):
    """Salva a lista de dispositivos descobertos em um arquivo JSON."""
    if not devices_list:
        print("\n[!] Nenhum dispositivo para salvar no arquivo JSON.")
        return

    try:
        # [DEBUG] Mostra quantos dispositivos serão salvos
        print(f"\n[DEBUG] Preparando para salvar {len(devices_list)} dispositivos no arquivo '{filename}'...")
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

        print("\n" + "="*50)
        print("[*] INICIANDO FASE DE VARREDURA ATIVA")
        print("="*50)
        all_found_devices = {} 
        for subnet in target_subnets:
            found_clients_on_subnet = _scan_arp_on_subnet(subnet)
            for client in found_clients_on_subnet:
                if client['ip'] not in all_found_devices:
                    # [DEBUG] Informa sobre um novo dispositivo adicionado à lista final
                    print(f"    [DEBUG] Adicionando novo dispositivo à lista final: {client['ip']}")
                    print("\n[*] Iniciando escaneamento de portas")
                    portas = escanear_portas(client['ip'])
                    all_found_devices[client['ip']] = client
                    client["portas"] = portas
                else:
                    # [DEBUG] Informa se um dispositivo foi visto novamente (em outra sub-rede, por exemplo)
                    print(f"    [DEBUG] Dispositivo {client['ip']} já estava na lista. Atualizando informações.")
                    all_found_devices[client['ip']] = client # Atualiza caso haja alguma info nova
                    client["portas"] = portas
        
        print("\n[*] Descoberta de IPs concluída.")
        # [DEBUG] Mostra um resumo final dos IPs únicos encontrados
        final_ips = list(all_found_devices.keys())
        final_ips.sort(key=ipaddress.ip_address)
        print(f"[DEBUG] Total de {len(final_ips)} dispositivos únicos encontrados em todas as sub-redes: {final_ips}")
        
        return list(all_found_devices.values())

    except PermissionError:
        print("\n[ERRO FATAL] A descoberta completa precisa ser executada com privilégios de administrador/root.")
        return None
    except KeyboardInterrupt:
        print("\n[!] Processo interrompido pelo usuário.")
        return None
    except Exception as e:
        print(f"\n[ERRO INESPERADO NA DESCOBERTA] {e}")
        return None

# Bloco de execução principal
if __name__ == "__main__":
    print("--- INICIANDO SCRIPT DE DESCOBERTA DE REDE ---")
    # Aumente o passive_timeout se sua rede for muito "quieta"
    discovered_devices = run_full_discovery(passive_timeout=60)
    
    if discovered_devices is not None:
        save_discoveries_to_json(discovered_devices)
    else:
        print("\n--- SCRIPT ENCERRADO COM ERRO ---")
        
    print("\n--- EXECUÇÃO FINALIZADA ---")