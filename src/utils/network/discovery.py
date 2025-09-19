import ipaddress
import json
from scapy.all import sniff, srp, Ether, ARP, IP, conf
from src.utils.network.portas import escanear_portas
from src.utils.permissao.permissao import verificar_permissoes
from src.utils.log.log import setup_logger

logger = setup_logger()

# [DEBUG] Aumenta o nível de verbosidade do Scapy para depuração
# conf.verb = 1 

def _discover_subnets_passively(timeout=60):
    if not verificar_permissoes:
        logger.warning({
            "evento": "Permissoes insuficientes",
            "detalhes": "Execute como administrador/root para descoberta completa."
        })
        return

    logger.info({
        "evento": "Iniciando escuta passiva",
        "detalhes": f"Tempo limite de {timeout} segundos"
    })

    discovered_ips = set()

    def packet_handler(packet):
        if packet.haslayer(ARP):
            ip_src = packet[ARP].psrc
            logger.debug({"evento": "ARP detectado", "ip": ip_src})
            discovered_ips.add(ip_src)
        elif packet.haslayer(IP):
            ip_src = packet[IP].src
            logger.debug({"evento": "Pacote IP detectado", "ip": ip_src})
            discovered_ips.add(ip_src)

    sniff(prn=packet_handler, store=0, timeout=timeout)

    logger.info({
        "evento": "IPs passivamente capturados",
        "total": len(discovered_ips),
        "ips": list(discovered_ips)
    })

    if not discovered_ips:
        return []

    subnets = set()
    for ip in discovered_ips:
        try:
            ip_obj = ipaddress.ip_address(ip)
            if not ip_obj.is_loopback and not ip_obj.is_multicast and not ip_obj.is_private:
                logger.debug({"evento": "Ignorando IP não privado", "ip": ip})
                continue

            network = ipaddress.ip_network(f"{ip}/24", strict=False)
            logger.debug({"evento": "Sub-rede mapeada", "ip": ip, "subnet": str(network)})
            subnets.add(str(network))
        except ValueError:
            logger.warning({"evento": "IP inválido", "valor": ip})
            continue

    logger.info({"evento": "Sub-redes ativas detectadas", "subnets": list(subnets)})
    return list(subnets)


def _scan_arp_on_subnet(network_range, timeout=3):
    """Executa um ARP scan e retorna lista de dispositivos encontrados."""
    logger.info({"evento": "Iniciando varredura ARP", "subnet": network_range})

    clients_list = []
    try:
        arp_request = ARP(pdst=network_range)
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        arp_request_broadcast = broadcast / arp_request

        logger.debug({"evento": "Enviando pacote ARP", "subnet": network_range})

        answered_list, unanswered_list = srp(arp_request_broadcast, timeout=timeout, verbose=0)

        logger.debug({
            "evento": "Resultados ARP",
            "respostas": len(answered_list),
            "sem_resposta": len(unanswered_list)
        })

        if not answered_list:
            logger.warning({"evento": "Nenhum dispositivo respondeu", "subnet": network_range})
            return []

        for sent_packet, received_packet in answered_list:
            client_info = {
                "ip": received_packet.psrc,
                "mac": received_packet.hwsrc,
                "subnet": network_range
            }
            logger.debug({"evento": "Dispositivo encontrado", **client_info})
            clients_list.append(client_info)

        logger.info({"evento": "Dispositivos encontrados", "total": len(clients_list), "subnet": network_range})
        return clients_list

    except Exception as e:
        logger.error({"evento": "Erro durante scan ARP", "subnet": network_range, "detalhes": str(e)})
        return []


def save_discoveries_to_json(devices_list, filename="data/discovery_results.json"): 
    """Salva a lista de dispositivos descobertos em JSON."""
    if not devices_list:
        logger.warning({"evento": "Nenhum dispositivo para salvar"})
        return

    

    try:
        sorted_list = sorted(devices_list, key=lambda x: ipaddress.ip_address(x['ip']))
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(sorted_list, f, indent=4, ensure_ascii=False)

        logger.info({"evento": "Relatório salvo", "arquivo": filename, "total_dispositivos": len(sorted_list)})
    except Exception as e:
        logger.error({"evento": "Erro ao salvar arquivo JSON", "arquivo": filename, "detalhes": str(e)})




def run_full_discovery(passive_timeout=60):
    """Orquestra descoberta passiva e ativa de rede."""
    try:
        target_subnets = _discover_subnets_passively(timeout=passive_timeout)
        if not target_subnets:   
            logger.warning({"evento": "Nenhuma sub-rede ativa descoberta"})
            return []

        logger.info({"evento": "Iniciando varredura ativa", "subnets": target_subnets})

        all_found_devices = {}

        for subnet in target_subnets:
            found_clients_on_subnet = _scan_arp_on_subnet(subnet)
            for client in found_clients_on_subnet:
                if client['ip'] not in all_found_devices:
                    logger.debug({"evento": "Novo dispositivo adicionado", "ip": client['ip']})
                    portas = escanear_portas(client['ip'])
                    client["portas"] = portas
                    all_found_devices[client['ip']] = client
                else:
                    logger.debug({"evento": "Dispositivo já presente. Atualizando", "ip": client['ip']})
                    portas = escanear_portas(client['ip'])
                    client["portas"] = portas
                    all_found_devices[client['ip']] = client

        final_ips = list(all_found_devices.keys())
        final_ips.sort(key=ipaddress.ip_address)
        logger.info({"evento": "Descoberta concluída", "total_dispositivos": len(final_ips), "ips": final_ips})

        return list(all_found_devices.values())

    except PermissionError:
        logger.error({"evento": "Permissões insuficientes para descoberta completa"})
        return None
    except KeyboardInterrupt:
        logger.warning({"evento": "Processo interrompido pelo usuário"})
        return None
    except Exception as e:
        logger.error({"evento": "Erro inesperado na descoberta", "detalhes": str(e)})
        return None


if __name__ == "__main__":
    logger.info({"evento": "--- INICIANDO SCRIPT DE DESCOBERTA DE REDE ---"})
    discovered_devices = run_full_discovery(passive_timeout=60)
    
    if discovered_devices is not None:
        save_discoveries_to_json(discovered_devices)
    else:
        logger.error({"evento": "Script finalizado com erro"})

    logger.info({"evento": "--- EXECUÇÃO FINALIZADA ---"})
