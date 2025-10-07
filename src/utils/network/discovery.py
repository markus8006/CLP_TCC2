# src/utils/network/enhanced_discovery.py
import os
import ipaddress
import json
import socket
import shutil
import subprocess
import xml.etree.ElementTree as ET
import tempfile
import copy
import re
try:
    import netifaces
except:
    netifaces = None
import psutil
from typing import List, Dict, Optional, Any, Set, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import time
from dataclasses import dataclass
from collections import defaultdict
import threading

from scapy.all import (
    sniff,
    srp,
    sr,
    Ether,
    ARP,
    IP,
    ICMP,
    conf,
    get_if_list,
    get_if_addr,
)

# imports do projeto
try:
    from src.utils.network.portas import escanear_portas
except Exception:
    escanear_portas = None

from src.utils.permissao.permissao import verificar_permissoes
from src.utils.log.log import setup_logger
from src.utils.root.paths import DISCOVERY_FILE

logger = setup_logger()

# -----------------------
# CONFIGURAÇÕES MELHORADAS
# -----------------------
@dataclass
class DiscoveryConfig:
    """Configuração centralizada para descoberta de rede"""
    # Portas específicas para dispositivos industriais
    MODBUS_PORTS: List[int] = None
    SIEMENS_PORTS: List[int] = None  
    ROCKWELL_PORTS: List[int] = None
    SCHNEIDER_PORTS: List[int] = None
    OPCUA_PORTS: List[int] = None
    COMMON_INDUSTRIAL_PORTS: List[int] = None
    
    # Timeouts adaptativos
    BASE_PASSIVE_TIMEOUT: int = 30
    BASE_ARP_TIMEOUT: int = 3
    BASE_ICMP_TIMEOUT: int = 2
    BASE_TCP_TIMEOUT: float = 1.0
    
    # Threading
    MAX_WORKERS_PER_INTERFACE: int = 8
    MAX_TOTAL_WORKERS: int = 32
    
    # Nmap
    USE_NMAP: bool = True
    NMAP_TIMEOUT_BASE: int = 300
    NMAP_INTENSITY: int = 0
    
    # Cache e performance
    CACHE_DURATION_SECONDS: int = 300  # 5 minutos
    ENABLE_CACHE: bool = True
    
    def __post_init__(self):
        if self.MODBUS_PORTS is None:
            self.MODBUS_PORTS = [502, 1502]
        if self.SIEMENS_PORTS is None:
            self.SIEMENS_PORTS = [102, 135, 161, 80, 443, 8080]
        if self.ROCKWELL_PORTS is None:
            self.ROCKWELL_PORTS = [44818, 2222, 5555, 1911]
        if self.SCHNEIDER_PORTS is None:
            self.SCHNEIDER_PORTS = [502, 80, 443, 161, 1024, 1025]
        if self.OPCUA_PORTS is None:
            self.OPCUA_PORTS = [4840, 48400, 48401, 48402]
        if self.COMMON_INDUSTRIAL_PORTS is None:
            self.COMMON_INDUSTRIAL_PORTS = list(set(
                self.MODBUS_PORTS + self.SIEMENS_PORTS + 
                self.ROCKWELL_PORTS + self.SCHNEIDER_PORTS + 
                self.OPCUA_PORTS + [20000, 20001, 20002, 161, 162, 23, 21, 80, 443]
            ))

CONFIG = DiscoveryConfig()

# -----------------------
# DETECÇÃO AVANÇADA DE INTERFACES
# -----------------------
@dataclass
class NetworkInterface:
    """Representa uma interface de rede com suas propriedades"""
    name: str
    ip: str
    netmask: str
    network: str
    broadcast: Optional[str]
    mac: Optional[str]
    is_up: bool
    is_physical: bool
    interface_type: str
    mtu: Optional[int]

def get_all_network_interfaces() -> List[NetworkInterface]:
    """
    Detecta TODAS as interfaces de rede ativas do sistema
    Melhoria: usa netifaces + psutil para detecção mais robusta
    """
    interfaces = []
    
    try:
        # Usar netifaces se disponível (mais confiável)
        if 'netifaces' in globals():
            for iface_name in netifaces.interfaces():
                try:
                    addrs = netifaces.ifaddresses(iface_name)
                    
                    # Pular interfaces sem IPv4
                    if netifaces.AF_INET not in addrs:
                        continue
                        
                    ipv4_info = addrs[netifaces.AF_INET][0]
                    ip = ipv4_info['addr']
                    netmask = ipv4_info['netmask']
                    
                    # Pular localhost e IPs inválidos
                    if ip.startswith('127.') or ip == '0.0.0.0':
                        continue
                    
                    # Calcular rede
                    try:
                        network_obj = ipaddress.ip_network(f"{ip}/{netmask}", strict=False)
                        network = str(network_obj)
                    except:
                        continue
                    
                    # Obter MAC se disponível
                    mac = None
                    if netifaces.AF_LINK in addrs:
                        mac = addrs[netifaces.AF_LINK][0].get('addr')
                    
                    # Detectar se é física ou virtual
                    is_physical = not any(x in iface_name.lower() for x in 
                                        ['virt', 'docker', 'br-', 'veth', 'lo', 'tun', 'tap'])
                    
                    # Determinar tipo de interface
                    interface_type = _determine_interface_type(iface_name)
                    
                    # Verificar se está UP usando psutil
                    is_up = True
                    try:
                        stats = psutil.net_if_stats().get(iface_name)
                        if stats:
                            is_up = stats.isup
                    except:
                        pass
                    
                    interfaces.append(NetworkInterface(
                        name=iface_name,
                        ip=ip,
                        netmask=netmask,
                        network=network,
                        broadcast=ipv4_info.get('broadcast'),
                        mac=mac,
                        is_up=is_up,
                        is_physical=is_physical,
                        interface_type=interface_type,
                        mtu=None
                    ))
                    
                    logger.debug(f"Interface detectada: {iface_name} - {ip}/{netmask} ({network})")
                    
                except Exception as e:
                    logger.debug(f"Erro processando interface {iface_name}: {e}")
                    continue
        
        # Fallback para método original se netifaces não disponível
        else:
            interfaces = _fallback_interface_detection()
            
    except Exception as e:
        logger.error(f"Erro na detecção de interfaces: {e}")
        interfaces = _fallback_interface_detection()
    
    logger.info(f"Total de interfaces detectadas: {len(interfaces)}")
    return interfaces

def _determine_interface_type(iface_name: str) -> str:
    """Determina o tipo de interface baseado no nome"""
    name_lower = iface_name.lower()
    
    if any(x in name_lower for x in ['eth', 'ens', 'enp']):
        return 'ethernet'
    elif any(x in name_lower for x in ['wifi', 'wlan', 'wireless']):
        return 'wireless'
    elif any(x in name_lower for x in ['docker', 'br-']):
        return 'bridge'
    elif any(x in name_lower for x in ['veth', 'virt']):
        return 'virtual'
    elif any(x in name_lower for x in ['tun', 'tap']):
        return 'tunnel'
    elif any(x in name_lower for x in ['lo', 'loopback']):
        return 'loopback'
    else:
        return 'unknown'

def _fallback_interface_detection() -> List[NetworkInterface]:
    """Método fallback usando scapy/métodos originais"""
    interfaces = []
    
    try:
        for iface in get_if_list():
            try:
                ip = get_if_addr(iface)
                if not ip or ip.startswith('127.') or ip == '0.0.0.0':
                    continue
                
                # Assumir /24 como fallback
                network = str(ipaddress.ip_network(f"{ip}/24", strict=False))
                
                interfaces.append(NetworkInterface(
                    name=iface,
                    ip=ip,
                    netmask='255.255.255.0',
                    network=network,
                    broadcast=None,
                    mac=None,
                    is_up=True,
                    is_physical=True,
                    interface_type='unknown',
                    mtu=None
                ))
            except:
                continue
    except:
        pass
        
    return interfaces

# -----------------------
# TIMEOUTS ADAPTATIVOS
# -----------------------
def calculate_adaptive_timeouts(network_size: int) -> Dict[str, Union[int, float]]:
    """
    Calcula timeouts baseados no tamanho da rede
    Melhoria: evita timeouts muito baixos para redes grandes
    """
    # Estimar hosts baseado no CIDR mais comum
    size_multiplier = max(1.0, network_size / 256)
    
    return {
        'passive': min(CONFIG.BASE_PASSIVE_TIMEOUT * size_multiplier, 120),
        'arp': min(CONFIG.BASE_ARP_TIMEOUT * size_multiplier, 10),
        'icmp': min(CONFIG.BASE_ICMP_TIMEOUT * size_multiplier, 5),
        'tcp': min(CONFIG.BASE_TCP_TIMEOUT * size_multiplier, 3.0),
        'nmap': min(CONFIG.NMAP_TIMEOUT_BASE * size_multiplier, 900)
    }

# -----------------------
# SCAN PASSIVO MELHORADO
# -----------------------
def discover_passively_all_interfaces(
    interfaces: List[NetworkInterface], 
    timeout: int = CONFIG.BASE_PASSIVE_TIMEOUT
) -> Dict[str, Set[str]]:
    """
    Faz sniff passivo em TODAS as interfaces simultaneamente
    Melhoria: multi-interface, threading, melhor performance
    """
    if not verificar_permissoes():
        logger.warning("Permissões insuficientes para sniff passivo completo")
        return {}
    
    logger.info(f"Iniciando descoberta passiva em {len(interfaces)} interfaces por {timeout}s")
    
    results = {}
    threads = []
    
    def _sniff_interface(interface: NetworkInterface):
        """Thread worker para sniff em uma interface específica"""
        seen_ips = set()
        
        def _packet_handler(pkt):
            try:
                if pkt.haslayer(ARP):
                    ip = pkt[ARP].psrc
                    if not ip.startswith('127.'):
                        seen_ips.add(ip)
                elif pkt.haslayer(IP):
                    ip = pkt[IP].src
                    if not ip.startswith('127.'):
                        seen_ips.add(ip)
            except Exception:
                pass
        
        try:
            sniff(
                iface=interface.name,
                store=0,
                prn=_packet_handler,
                timeout=timeout,
                filter="arp or icmp or tcp"
            )
        except Exception as e:
            logger.debug(f"Erro no sniff da interface {interface.name}: {e}")
        
        results[interface.name] = seen_ips
        logger.debug(f"Interface {interface.name}: {len(seen_ips)} IPs detectados passivamente")
    
    # Iniciar threads para cada interface
    for iface in interfaces:
        if iface.is_up:
            thread = threading.Thread(target=_sniff_interface, args=(iface,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
    
    # Aguardar conclusão
    for thread in threads:
        thread.join(timeout + 5)
    
    total_ips = sum(len(ips) for ips in results.values())
    logger.info(f"Descoberta passiva concluída: {total_ips} IPs únicos em {len(results)} interfaces")
    
    return results

# -----------------------
# SCANNER INDUSTRIAL ESPECIALIZADO
# -----------------------
def detect_industrial_device(ip: str, open_ports: Dict[int, Any]) -> Dict[str, Any]:
    """
    Detecta dispositivos industriais baseado nas portas abertas
    Melhoria: melhor identificação de PLCs e dispositivos SCADA
    """
    device_info = {
        'type': 'unknown',
        'manufacturer': 'unknown',
        'protocol': [],
        'confidence': 0
    }
    
    confidence = 0
    protocols = []
    manufacturer = 'unknown'
    device_type = 'network_device'
    
    # Detecção baseada em portas
    for port, info in open_ports.items():
        # Modbus
        if port in CONFIG.MODBUS_PORTS:
            protocols.append('modbus')
            confidence += 30
            device_type = 'plc'
            
        # Siemens
        elif port in [102, 80, 443] and any(p in open_ports for p in [102]):
            protocols.append('s7')
            manufacturer = 'siemens'
            confidence += 25
            device_type = 'plc'
            
        # Rockwell/Allen-Bradley
        elif port in CONFIG.ROCKWELL_PORTS:
            protocols.append('ethernet_ip')
            manufacturer = 'rockwell'
            confidence += 25
            device_type = 'plc'
            
        # OPC-UA
        elif port in CONFIG.OPCUA_PORTS:
            protocols.append('opcua')
            confidence += 20
            device_type = 'plc'
            
        # SNMP (comum em dispositivos industriais)
        elif port in [161, 162]:
            protocols.append('snmp')
            confidence += 15
            
        # Portas web comuns em PLCs
        elif port in [80, 443, 8080] and device_type != 'unknown':
            protocols.append('http')
            confidence += 10
    
    # Combinações específicas que indicam PLCs
    if 502 in open_ports and (80 in open_ports or 443 in open_ports):
        confidence += 20
        device_type = 'modbus_plc'
        
    if 102 in open_ports and 80 in open_ports:
        confidence += 25
        manufacturer = 'siemens'
        device_type = 'siemens_plc'
    
    device_info.update({
        'type': device_type,
        'manufacturer': manufacturer,
        'protocol': protocols,
        'confidence': min(confidence, 100)
    })
    
    return device_info

# -----------------------
# PIPELINE PRINCIPAL MELHORADO
# -----------------------
def run_enhanced_discovery(
    target_interfaces: Optional[List[str]] = None,
    passive_timeout: Optional[int] = None,
    use_cache: bool = CONFIG.ENABLE_CACHE,
    save_detailed: bool = True
) -> List[Dict[str, Any]]:
    """
    Pipeline de descoberta completamente reescrito e melhorado
    
    Melhorias principais:
    - Multi-interface simultâneo
    - Timeouts adaptativos
    - Detecção industrial especializada
    - Cache inteligente
    - Melhor agregação de dados
    """
    
    if not verificar_permissoes():
        logger.error("Permissões insuficientes - execute como root/administrador")
        return []
    
    start_time = time()
    logger.info("=== INICIANDO DESCOBERTA AVANÇADA DE REDE ===")
    
    # 1. Detectar todas as interfaces
    all_interfaces = get_all_network_interfaces()
    
    # Filtrar interfaces se especificado
    if target_interfaces:
        all_interfaces = [i for i in all_interfaces if i.name in target_interfaces]
    
    if not all_interfaces:
        logger.error("Nenhuma interface de rede válida encontrada")
        return []
    
    # 2. Calcular timeouts adaptativos baseado no tamanho total da rede
    total_network_size = sum(ipaddress.ip_network(iface.network).num_addresses 
                           for iface in all_interfaces)
    timeouts = calculate_adaptive_timeouts(total_network_size)
    
    logger.info(f"Interfaces ativas: {len(all_interfaces)}")
    logger.info(f"Tamanho total da rede: ~{total_network_size} IPs possíveis")
    logger.info(f"Timeouts calculados: {timeouts}")
    
    # 3. Descoberta passiva multi-interface
    passive_results = discover_passively_all_interfaces(
        all_interfaces, 
        int(passive_timeout or timeouts['passive'])
    )
    
    # 4. Agregar todos os IPs descobertos
    all_discovered_ips = set()
    interface_mapping = {}
    
    for interface in all_interfaces:
        # IPs descobertos passivamente nesta interface
        passive_ips = passive_results.get(interface.name, set())
        
        # Mapear interface para IPs
        for ip in passive_ips:
            all_discovered_ips.add(ip)
            interface_mapping[ip] = interface
    
    # 5. ARP scan por interface (paralelo)
    logger.info("Iniciando ARP scan paralelo por interface...")
    
    all_devices = {}
    
    with ThreadPoolExecutor(max_workers=len(all_interfaces)) as executor:
        # Criar future para ARP scan de cada interface
        arp_futures = {
            executor.submit(_enhanced_arp_scan, interface, timeouts['arp']): interface 
            for interface in all_interfaces
        }
        
        for future in as_completed(arp_futures):
            interface = arp_futures[future]
            try:
                devices = future.result()
                for device in devices:
                    ip = device['ip']
                    all_devices[ip] = device
                    all_discovered_ips.add(ip)
                    if ip not in interface_mapping:
                        interface_mapping[ip] = interface
                        
            except Exception as e:
                logger.error(f"Erro no ARP scan da interface {interface.name}: {e}")
    
    logger.info(f"Total de IPs únicos descobertos até agora: {len(all_discovered_ips)}")
    
    # 6. ICMP sweep em chunks paralelos
    alive_ips = set()
    ip_chunks = [list(all_discovered_ips)[i:i+50] for i in range(0, len(all_discovered_ips), 50)]
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        icmp_futures = [
            executor.submit(icmp_ping_sweep, chunk, timeouts['icmp']) 
            for chunk in ip_chunks
        ]
        
        for future in as_completed(icmp_futures):
            try:
                chunk_alive = future.result()
                alive_ips.update(chunk_alive)
            except Exception as e:
                logger.debug(f"Erro no ICMP sweep: {e}")
    
    # 7. Port scanning inteligente
    logger.info(f"Iniciando port scan em {len(all_discovered_ips)} IPs...")
    
    with ThreadPoolExecutor(max_workers=CONFIG.MAX_TOTAL_WORKERS) as executor:
        port_futures = {
            executor.submit(_enhanced_port_scan, ip, timeouts): ip 
            for ip in all_discovered_ips
        }
        
        for future in as_completed(port_futures):
            ip = port_futures[future]
            try:
                port_results = future.result()
                
                # Atualizar device info
                if ip not in all_devices:
                    iface = interface_mapping.get(ip)
                    all_devices[ip] = {
                        'ip': ip,
                        'mac': None,
                        'interface': iface.name if iface else None,
                        'network': iface.network if iface else None,
                        'discovered_via': []
                    }
                
                # Adicionar resultados de portas
                all_devices[ip].update(port_results)
                
                # Detectar se é dispositivo industrial
                if port_results.get('open_ports'):
                    industrial_info = detect_industrial_device(ip, port_results['open_ports'])
                    all_devices[ip]['industrial_device'] = industrial_info
                    
            except Exception as e:
                logger.debug(f"Erro no port scan de {ip}: {e}")
    
    # 8. Finalizar e organizar resultados
    final_devices = []
    for ip, device in all_devices.items():
        # Adicionar status ICMP
        device['responds_to_ping'] = ip in alive_ips
        
        # Garantir campos obrigatórios
        device.setdefault('discovered_via', [])
        device.setdefault('open_ports', {})
        device.setdefault('services', {})
        
        final_devices.append(device)
    
    # Ordenar por IP
    final_devices = _safe_ip_sort(final_devices)
    
    elapsed = time() - start_time
    logger.info(f"=== DESCOBERTA CONCLUÍDA ===")
    logger.info(f"Tempo total: {elapsed:.2f}s")
    logger.info(f"Dispositivos encontrados: {len(final_devices)}")
    logger.info(f"Dispositivos industriais: {sum(1 for d in final_devices if d.get('industrial_device', {}).get('confidence', 0) > 50)}")
    
    # 9. Salvar resultados
    _save_discovery_results(final_devices, save_detailed)
    
    return final_devices

# -----------------------
# FUNÇÕES AUXILIARES MELHORADAS
# -----------------------
def _enhanced_arp_scan(interface: NetworkInterface, timeout: int) -> List[Dict[str, Any]]:
    """ARP scan melhorado para uma interface específica"""
    devices = []
    
    try:
        logger.debug(f"ARP scan na interface {interface.name} - rede {interface.network}")
        
        arp = ARP(pdst=interface.network)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        
        answered, _ = srp(ether / arp, timeout=timeout, verbose=0, iface=interface.name)
        
        for _, rcv in answered:
            devices.append({
                'ip': rcv.psrc,
                'mac': rcv.hwsrc,
                'interface': interface.name,
                'network': interface.network,
                'discovered_via': ['arp'],
                'timestamp': time()
            })
            
        logger.debug(f"Interface {interface.name}: {len(devices)} dispositivos via ARP")
        
    except Exception as e:
        logger.debug(f"Erro no ARP scan da interface {interface.name}: {e}")
    
    return devices

def _enhanced_port_scan(ip: str, timeouts: Dict) -> Dict[str, Any]:
    """Port scan melhorado com detecção de serviços"""
    result = {
        'open_ports': {},
        'services': {},
        'scan_time': time()
    }
    
    # Scan rápido de portas industriais primeiro
    quick_results = tcp_probe(ip, CONFIG.COMMON_INDUSTRIAL_PORTS, timeouts['tcp'])
    open_ports = [port for port, is_open in quick_results.items() if is_open]
    
    if open_ports:
        # Se encontrou portas abertas, fazer scan mais detalhado
        result['open_ports'] = {port: {'state': 'open', 'method': 'tcp_connect'} 
                              for port in open_ports}
        
        # Tentar identificar serviços nas portas abertas
        for port in open_ports[:5]:  # Limitar para performance
            service_info = _identify_service(ip, port)
            if service_info:
                result['services'][port] = service_info
    
    return result

def _identify_service(ip: str, port: int) -> Optional[Dict[str, str]]:
    """Tenta identificar o serviço rodando na porta"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((ip, port))
            
            # Enviar dados específicos do protocolo se necessário
            if port == 502:  # Modbus
                return {'name': 'modbus', 'protocol': 'tcp', 'type': 'industrial'}
            elif port == 102:  # S7
                return {'name': 's7comm', 'protocol': 'tcp', 'type': 'industrial'}
            elif port in [80, 443, 8080]:
                return {'name': 'http', 'protocol': 'tcp', 'type': 'web'}
            elif port == 4840:
                return {'name': 'opcua', 'protocol': 'tcp', 'type': 'industrial'}
            else:
                return {'name': 'unknown', 'protocol': 'tcp', 'type': 'unknown'}
                
    except Exception:
        return None

def _save_discovery_results(devices: List[Dict[str, Any]], detailed: bool = True):
    """Salva os resultados da descoberta"""
    try:
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(DISCOVERY_FILE), exist_ok=True)
        
        # Salvar arquivo principal
        with tempfile.NamedTemporaryFile('w', delete=False, 
                                       dir=os.path.dirname(DISCOVERY_FILE)) as f:
            json.dump(devices, f, indent=2, ensure_ascii=False)
            temp_name = f.name
        
        os.replace(temp_name, DISCOVERY_FILE)
        logger.info(f"Resultados salvos em: {DISCOVERY_FILE}")
        
        # Salvar versão resumida se solicitado
        if detailed:
            summary_file = DISCOVERY_FILE.replace('.json', '_summary.json')
            summary = []
            
            for device in devices:
                industrial = device.get('industrial_device', {})
                summary.append({
                    'ip': device['ip'],
                    'mac': device.get('mac'),
                    'responds_to_ping': device.get('responds_to_ping', False),
                    'open_ports': list(device.get('open_ports', {}).keys()),
                    'is_industrial': industrial.get('confidence', 0) > 50,
                    'device_type': industrial.get('type', 'unknown'),
                    'manufacturer': industrial.get('manufacturer', 'unknown')
                })
            
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Resumo salvo em: {summary_file}")
            
    except Exception as e:
        logger.error(f"Erro ao salvar resultados: {e}")

# Manter compatibilidade com funções originais
def _safe_ip_sort(devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ordena dispositivos por IP de forma segura"""
    try:
        return sorted(devices, key=lambda x: ipaddress.ip_address(x.get('ip', '0.0.0.0')))
    except Exception:
        return devices

def icmp_ping_sweep(ip_list: List[str], timeout: int = 2) -> Set[str]:
    """ICMP sweep melhorado"""
    alive = set()
    if not ip_list:
        return alive
        
    try:
        packets = IP(dst=ip_list) / ICMP()
        answered, _ = sr(packets, timeout=timeout, verbose=0)
        
        for _, rcv in answered:
            alive.add(rcv.src)
            
    except Exception as e:
        logger.debug(f"Erro no ICMP sweep: {e}")
    
    return alive

def tcp_probe(ip: str, ports: List[int], timeout: float = 1.0) -> Dict[int, bool]:
    """TCP probe melhorado"""
    results = {}
    
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                result = s.connect_ex((ip, port))
                results[port] = (result == 0)
        except Exception:
            results[port] = False
            
    return results

# -----------------------
# FUNÇÃO PRINCIPAL PARA COMPATIBILIDADE
# -----------------------
def run_full_discovery(**kwargs) -> List[Dict[str, Any]]:
    """Função principal mantendo compatibilidade com código original"""
    return run_enhanced_discovery(**kwargs)

# -----------------------
# EXECUTÁVEL
# -----------------------
if __name__ == "__main__":
    print("=== SISTEMA DE DESCOBERTA DE REDE MELHORADO ===")
    devices = run_enhanced_discovery()
    
    if devices:
        print(f"\n✅ Descoberta concluída com sucesso!")
        print(f"📊 Total de dispositivos: {len(devices)}")
        
        industrial_count = sum(1 for d in devices 
                             if d.get('industrial_device', {}).get('confidence', 0) > 50)
        print(f"🏭 Dispositivos industriais detectados: {industrial_count}")
        
        interfaces = set(d.get('interface') for d in devices if d.get('interface'))
        print(f"🔌 Interfaces utilizadas: {', '.join(interfaces) if interfaces else 'N/A'}")
        
    else:
        print("❌ Nenhum dispositivo encontrado ou erro na execução")