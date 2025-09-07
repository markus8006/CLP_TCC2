import sys
import socket
import ipaddress
import psutil
import time
from scapy.all import sniff, srp, Ether, ARP, IP

# Nota: Esta função não é usada no fluxo principal, mas está aqui caso precise dela no futuro.
# O typo no nome foi corrigido para 'get_local_subnets'.
def get_local_subnets():
    """Busca todas as interfaces de rede do computador, encontra todos os IPs IPv4
    configurados e retorna uma lista de suas sub-redes sem duplicatas."""
    subnets = set()
    all_interfaces = psutil.net_if_addrs()
    for interface_name, addresses in all_interfaces.items():
        for addr in addresses:
            if addr.family == socket.AF_INET and addr.netmask:
                try:
                    ip_interface = ipaddress.ip_interface(f"{addr.address}/{addr.netmask}")
                    if ip_interface.is_loopback:
                        continue
                    network = ip_interface.network
                    subnets.add(str(network))
                except ValueError:
                    continue
    if not subnets:
        print("[!] Nenhuma sub-rede local válida foi encontrada.")
    return list(subnets)


def discover_subnets_passively(timeout=60):
    """Escuta passivamente o tráfego da rede por um tempo para identificar
    os IPs e as sub-redes que estão se comunicando."""
    print(f"[*] Fase 1: Ouvindo passivamente o tráfego da rede por {timeout} segundos...")
    print("[*] Por favor, aguarde... (Ligar e desligar um CLP pode acelerar a descoberta)")
    discovered_ips = set()

    def packet_handler(packet):
        """Função que processa cada pacote capturado."""
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
            
    print(f"\n[+] Sub-redes ativas detectadas passivamente: {list(subnets)}")
    return list(subnets)


def scan_arp_on_subnet(network_range, timeout=3):
    """Executa um ARP scan ativo em uma única faixa de rede."""
    print(f"[*] Fase 2: Varrendo ativamente a sub-rede {network_range}...")
    try:
        arp_request = ARP(pdst=network_range)
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        arp_request_broadcast = broadcast / arp_request
        answered_list = srp(arp_request_broadcast, timeout=timeout, verbose=False)[0]

        clients_list = []
        for element in answered_list:
            clients_list.append({"ip": element[1].psrc, "mac": element[1].hwsrc})
        
        # CORRIGIDO: O 'return' foi movido para fora do loop 'for'.
        return clients_list 
        
    except PermissionError:
        raise PermissionError("Erro de Permissão: Execute como administrador/root.")
    except Exception as e:
        print(f"[!] Erro durante o scan em {network_range}: {e}")
        return []


def save_ips(clients_list, filename="ips_encontrados.txt"):
    """Salva a lista final de IPs em um arquivo."""
    
    # CORRIGIDO: A chave do dicionário é "ip" (minúscula), não "IP".
    ips = {client["ip"] for client in clients_list} 
    
    with open(filename, "w") as f:
        for ip in sorted(list(ips), key=ipaddress.ip_address):
            f.write(ip + "\n")
    print(f"\n[*] Tarefa concluída! Lista de {len(ips)} IPs únicos salva em '{filename}'")


if __name__ == "__main__":
    try:
        target_subnets = discover_subnets_passively(timeout=60)

        if not target_subnets:
            print("\n[!] Não foi possível descobrir sub-redes ativas. Encerrando.")
            exit()
            
        print("\n" + "="*40)
        all_found_clients = []
        for subnet in target_subnets:
            found_clients = scan_arp_on_subnet(subnet)
            all_found_clients.extend(found_clients)
            print(f"[+] Encontrados {len(found_clients)} dispositivos em {subnet}.")
        
        if all_found_clients:
            print("\n\n--- RELATÓRIO FINAL DE DISPOSITIVOS ENCONTRADOS ---")
            unique_clients = {client['ip']: client for client in all_found_clients}.values()
            
            print("IP Address\t\tMAC Address")
            print("-----------------------------------------")
            for client in sorted(unique_clients, key=lambda x: ipaddress.ip_address(x['ip'])):
                print(f"{client['ip']}\t\t{client['mac']}")
            print("-----------------------------------------")
            
            save_ips(list(unique_clients))
        else:
            print("\n\nNenhum dispositivo respondeu à varredura ativa.")

    except PermissionError as e:
        print(f"\n[ERRO FATAL] {e}")
    except KeyboardInterrupt:
        print("\n[!] Processo interrompido pelo usuário.")
    except Exception as e:
        print(f"\n[ERRO INESPERADO] {e}")