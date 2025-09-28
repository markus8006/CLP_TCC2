# src/utils/network/discovery.py
import ipaddress
import json
import socket
from typing import List, Dict, Optional, Any, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import time

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

from src.utils.network.portas import escanear_portas  # seu scanner atual, usado como fallback/extra
from src.utils.permissao.permissao import verificar_permissoes
from src.utils.log.log import setup_logger
from src.utils.root.paths import DISCOVERY_FILE

logger = setup_logger()

# portas típicas de PLC / serviços industriais
COMMON_PLC_PORTS: List[int] = [502, 102, 44818, 1911, 161, 4840]  # Modbus, S7, EtherNet/IP, Rockwell, SNMP, OPC-UA

# parâmetros configuráveis
DEFAULT_PASSIVE_TIMEOUT = 30
DEFAULT_ARP_TIMEOUT = 2
DEFAULT_ICMP_TIMEOUT = 1
DEFAULT_TCP_TIMEOUT = 0.5
MAX_WORKERS = 16  # threads



# -----------------------
# utilitários
# -----------------------
def _safe_ip_sort(devs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    try:
        return sorted(devs, key=lambda x: ipaddress.ip_address(x["ip"]))
    except Exception:
        return devs


def _read_arp_cache() -> Dict[str, str]:
    """Tenta ler o ARP cache do sistema como complemento (ip -> mac)."""
    arp_map: Dict[str, str] = {}
    try:
        # Linux: parse `ip neigh` output
        with os.popen("ip neigh") as p:
            out = p.read().strip().splitlines()
        for line in out:
            parts = line.split()
            if len(parts) >= 5:
                ip = parts[0]
                # mac aparece depois de 'lladdr' ou na 4ª posição
                if "lladdr" in parts:
                    idx = parts.index("lladdr") + 1
                    mac = parts[idx] if idx < len(parts) else None
                else:
                    mac = parts[4] if len(parts) > 4 else None
                if mac:
                    arp_map[ip] = mac
    except Exception:
        # fallback: tentar `arp -n`
        try:
            with os.popen("arp -n") as p:
                out = p.read().strip().splitlines()
            for line in out[1:]:
                fields = line.split()
                if fields and len(fields) >= 3:
                    ip = fields[0]
                    mac = fields[2]
                    arp_map[ip] = mac
        except Exception:
            pass
    return arp_map


# -----------------------
# Passive discovery (sniff)
# -----------------------
def discover_passively(timeout: int = DEFAULT_PASSIVE_TIMEOUT) -> Set[str]:
    """
    Sniff passivamente na(s) interfaces configuradas por `timeout` segundos.
    Retorna um set de IPs observados.
    """
    if not verificar_permissoes():
        logger.warning({
            "evento": "Permissoes insuficientes (passive)",
            "detalhes": "Execute como root/administrador para sniff passivo completo."
        })
        return set()

    logger.info({"evento": "Iniciando descoberta passiva", "timeout": timeout})
    seen_ips: Set[str] = set()

    def _pkt_handler(pkt):
        try:
            if pkt.haslayer(ARP):
                ip = pkt[ARP].psrc
                seen_ips.add(ip)
                logger.debug({"evento": "ARP detectado (passivo)", "ip": ip})
            elif pkt.haslayer(IP):
                ip = pkt[IP].src
                seen_ips.add(ip)
                logger.debug({"evento": "IP detectado (passivo)", "ip": ip})
        except Exception as e:
            logger.debug({"evento": "Erro handler passivo", "detalhes": str(e)})

    # sniff global (padrão scapy tenta em todas interfaces)
    sniff(store=0, prn=_pkt_handler, timeout=timeout)
    logger.info({"evento": "Descoberta passiva concluída", "total": len(seen_ips)})
    return seen_ips


# -----------------------
# Subnets por interface
# -----------------------
def get_local_subnets() -> Set[Tuple[str, str]]:
    """
    Retorna um set de (iface, subnet) onde subnet é CIDR string ex: '192.168.1.0/24'.
    Usa scapy.conf.ifaces ou get_if_list/get_if_addr para robustez.
    """
    subnets: Set[Tuple[str, str]] = set()

    # 1) tentar conf.ifaces (mais info: inclui netmask)
    try:
        for iface_name, iface_data in conf.ifaces.items():
            ip = getattr(iface_data, "ip", None)
            netmask = getattr(iface_data, "netmask", None)
            if not ip or ip.startswith("127.") or not netmask:
                continue
            try:
                iface = ipaddress.ip_interface(f"{ip}/{netmask}")
                net = str(iface.network)
                subnets.add((iface_name, net))
                logger.info({"evento": "Interface detectada", "iface": iface_name, "ip": ip, "subnet": net})
            except Exception as e:
                logger.debug({"evento": "Ignorando interface (erro parse)", "iface": iface_name, "detalhes": str(e)})
    except Exception:
        logger.debug({"evento": "Falha ao ler conf.ifaces; tentando get_if_list()"})

    # 2) fallback para get_if_list/get_if_addr com /24 por padrão
    if not subnets:
        for iface in get_if_list():
            try:
                ip = get_if_addr(iface)
                if not ip or ip.startswith("127."):
                    continue
                # heurística: assumir /24 se não houver netmask conhecida
                try:
                    net = str(ipaddress.ip_network(f"{ip}/24", strict=False))
                    subnets.add((iface, net))
                    logger.info({"evento": "Interface (fallback) detectada", "iface": iface, "ip": ip, "subnet": net})
                except Exception:
                    continue
            except Exception:
                continue

    return subnets


# -----------------------
# ARP scan ativo
# -----------------------
def arp_scan(network_cidr: str, timeout: int = DEFAULT_ARP_TIMEOUT) -> List[Dict[str, str]]:
    """
    Executa ARP scan na faixa indicada (ex: '192.168.1.0/24').
    Retorna lista de dicts: {'ip':..., 'mac':..., 'subnet': ...}
    """
    results: List[Dict[str, str]] = []
    try:
        arp = ARP(pdst=network_cidr)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        answered, _ = srp(ether / arp, timeout=timeout, verbose=0)
        for _, rcv in answered:
            results.append({"ip": rcv.psrc, "mac": rcv.hwsrc, "subnet": network_cidr})
        logger.info({"evento": "ARP scan concluído", "subnet": network_cidr, "found": len(results)})
    except PermissionError as e:
        logger.error({"evento": "Permissão negada para ARP scan", "detalhes": str(e)})
    except Exception as e:
        logger.error({"evento": "Erro no ARP scan", "subnet": network_cidr, "detalhes": str(e)})
    return results


# -----------------------
# ICMP sweep (ping)
# -----------------------
def icmp_ping_sweep(ip_list: List[str], timeout: int = DEFAULT_ICMP_TIMEOUT) -> Set[str]:
    """
    Envia ICMP echo para uma lista de IPs (usando scapy sr com vários destinos).
    Retorna set de IPs que responderam.
    """
    alive: Set[str] = set()
    if not ip_list:
        return alive

    try:
        # scapy aceita IP(dst=[]) para múltiplos destinos
        packets = IP(dst=ip_list) / ICMP()
        answered, _ = sr(packets, timeout=timeout, verbose=0)
        for snd, rcv in answered:
            try:
                alive.add(rcv.src)
            except Exception:
                continue
    except Exception as e:
        logger.debug({"evento": "Erro no ICMP sweep", "detalhes": str(e)})

    return alive


# -----------------------
# TCP probe simples
# -----------------------
def tcp_probe(ip: str, ports: List[int], timeout: float = DEFAULT_TCP_TIMEOUT) -> Dict[int, bool]:
    """
    Tenta conexão TCP simples (connect_ex) nas portas fornecidas.
    Retorna dict {porta: True/False}.
    """
    results: Dict[int, bool] = {}
    for p in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                res = s.connect_ex((ip, p))
                results[p] = (res == 0)
        except Exception:
            results[p] = False
    return results


# -----------------------
# Orquestrador principal
# -----------------------
def run_full_discovery(
    passive_timeout: int = DEFAULT_PASSIVE_TIMEOUT,
    arp_timeout: int = DEFAULT_ARP_TIMEOUT,
    icmp_timeout: int = DEFAULT_ICMP_TIMEOUT,
    tcp_timeout: float = DEFAULT_TCP_TIMEOUT,
    ports: Optional[List[int]] = None,
    parallel_workers: int = MAX_WORKERS,
    save_per_interface: bool = False,
) -> List[Dict[str, Any]]:
    """
    Executa: descoberta passiva -> obtém subnets por interface -> ARP scan por subnet (paralelo)
                 -> ICMP sweep em hosts descobertos -> TCP probes em portas comuns
    Retorna lista de dispositivos com campos:
      ip, mac (se conhecido), subnet, iface (se conhecido), alive_icmp, portas (dict), discovered_via (list)
    """
    if ports is None:
        ports = COMMON_PLC_PORTS

    if not verificar_permissoes():
        logger.error({"evento": "Permissões insuficientes (discovery)", "detalhes": "Executar como root/adm."})
        return []

    start_ts = time()
    logger.info({"evento": "Começando descoberta completa"})

    # 1) sniff passivo (coleta IPs observados)
    passive_ips = discover_passively(timeout=passive_timeout)

    # 2) obter subnets por interface
    iface_subnets = get_local_subnets()  # set of (iface, cidr)
    if not iface_subnets:
        logger.warning({"evento": "Nenhuma interface/sub-rede detectada"})
        return []

    # 3) ARP scan por subnet (paralelo)
    all_devices: Dict[str, Dict[str, Any]] = {}
    arp_futures = []
    with ThreadPoolExecutor(max_workers=parallel_workers) as ex:
        for iface, subnet in iface_subnets:
            arp_futures.append(ex.submit(arp_scan, subnet, arp_timeout))

        for fut in as_completed(arp_futures):
            try:
                devices = fut.result()
            except Exception as e:
                logger.debug({"evento": "Erro em ARP future", "detalhes": str(e)})
                devices = []
            for d in devices:
                ip = d["ip"]
                if ip not in all_devices:
                    all_devices[ip] = {
                        "ip": ip,
                        "mac": d.get("mac"),
                        "subnet": d.get("subnet"),
                        "iface": None,  # será preenchido abaixo se possível
                        "discovered_via": ["arp"],
                        "alive_icmp": False,
                        "portas": {},
                    }
                else:
                    if "arp" not in all_devices[ip]["discovered_via"]:
                        all_devices[ip]["discovered_via"].append("arp")
                    if not all_devices[ip].get("mac"):
                        all_devices[ip]["mac"] = d.get("mac")

    # 4) marcar IPs passivos que não foram pegos por ARP
    for ip in passive_ips:
        if ip not in all_devices:
            all_devices[ip] = {
                "ip": ip,
                "mac": None,
                "subnet": None,
                "iface": None,
                "discovered_via": ["passive"],
                "alive_icmp": False,
                "portas": {},
            }
        else:
            if "passive" not in all_devices[ip]["discovered_via"]:
                all_devices[ip]["discovered_via"].append("passive")

    # 5) tentar identificar iface/subnet para cada device baseado nas subnets conhecidas
    for iface, subnet in iface_subnets:
        net = ipaddress.ip_network(subnet)
        for ip, entry in all_devices.items():
            try:
                if ipaddress.ip_address(ip) in net:
                    entry["iface"] = iface
                    if not entry.get("subnet"):
                        entry["subnet"] = subnet
            except Exception:
                continue

    # 6) complementar com ARP cache do sistema
    try:
        import os  # import local para evitar top-level dependency if not needed
        arp_cache = _read_arp_cache()
        for ip, mac in arp_cache.items():
            if ip in all_devices and not all_devices[ip].get("mac"):
                all_devices[ip]["mac"] = mac
    except Exception:
        arp_cache = {}

    # 7) ICMP sweep (paralelo por chunks) para todos IPs descobertos para marcar alive
    ips_list = list(all_devices.keys())
    alive_ips = set()
    # sr with many targets: do in chunks of 200 to avoid packet explosion
    chunk = 200
    for i in range(0, len(ips_list), chunk):
        sub = ips_list[i : i + chunk]
        alive = icmp_ping_sweep(sub, timeout=icmp_timeout)
        alive_ips.update(alive)

    for ip in alive_ips:
        if ip in all_devices:
            all_devices[ip]["alive_icmp"] = True
            if "icmp" not in all_devices[ip]["discovered_via"]:
                all_devices[ip]["discovered_via"].append("icmp")

    # 8) TCP probes em portas comuns (paralelo por host)
    with ThreadPoolExecutor(max_workers=parallel_workers) as ex:
        future_map = {ex.submit(tcp_probe, ip, ports, tcp_timeout): ip for ip in all_devices.keys()}
        for fut in as_completed(future_map):
            ip = future_map[fut]
            try:
                res = fut.result()
                all_devices[ip]["portas"] = res
                # se alguma porta aberta, marca discovered_via
                if any(res.values()) and "tcp" not in all_devices[ip]["discovered_via"]:
                    all_devices[ip]["discovered_via"].append("tcp")
            except Exception as e:
                logger.debug({"evento": "Erro tcp_probe", "ip": ip, "detalhes": str(e)})

    # 9) fallback: usar seu escanear_portas (se quiser mais detalhes)
    #    (opcional) se escanear_portas for mais completo, pode usá-lo para hosts com portas abertas detectadas
    try:
        with ThreadPoolExecutor(max_workers=parallel_workers) as ex:
            futures = {}
            for ip, entry in all_devices.items():
                # se já detectou alguma porta aberta no tcp_probe, ou se quer varrer todos, usamos o scanner customizado
                if any(entry.get("portas", {}).values()):
                    futures[ex.submit(escanear_portas, ip)] = ip
            for fut in as_completed(futures):
                ip = futures[fut]
                try:
                    portas_detalhadas = fut.result()
                    all_devices[ip]["portas_detalhadas"] = portas_detalhadas
                except Exception as e:
                    logger.debug({"evento": "Erro escanear_portas future", "ip": ip, "detalhes": str(e)})
    except Exception:
        # se escanear_portas não existir ou der problema, ignora
        pass

    # resultado final
    devices_final = list(all_devices.values())
    devices_final = _safe_ip_sort(devices_final)

    elapsed = time() - start_ts
    logger.info({"evento": "Descoberta completa", "total": len(devices_final), "tempo_segundos": elapsed})

    # 10) salvar resultados
    try:
        with open(DISCOVERY_FILE, "w", encoding="utf-8") as f:
            json.dump(devices_final, f, indent=2, ensure_ascii=False)
        logger.info({"evento": "Resultados salvos", "arquivo": DISCOVERY_FILE})
    except Exception as e:
        logger.error({"evento": "Falha ao salvar resultados", "detalhes": str(e)})

    # salvar por interface (opcional)
    if save_per_interface:
        by_iface: Dict[str, List[Dict[str, Any]]] = {}
        for d in devices_final:
            iface = d.get("iface") or "unknown"
            by_iface.setdefault(iface, []).append(d)
        for iface, lst in by_iface.items():
            fname = f"{DISCOVERY_FILE.rstrip('.json')}_{iface}.json"
            try:
                with open(fname, "w", encoding="utf-8") as f:
                    json.dump(lst, f, indent=2, ensure_ascii=False)
                logger.info({"evento": "Salvo por interface", "iface": iface, "arquivo": fname})
            except Exception as e:
                logger.warning({"evento": "Erro salvando por interface", "iface": iface, "detalhes": str(e)})

    return devices_final


# -----------------------
# função helper para uso em background (como antes)
# -----------------------
def discovery_background_once() -> None:
    logger.info({"evento": "Iniciando discovery_background_once"})
    try:
        run_full_discovery()
    except Exception as e:
        logger.error({"evento": "Erro discovery_background_once", "detalhes": str(e)})


# -----------------------
# se executado diretamente
# -----------------------
if __name__ == "__main__":
    logger.info({"evento": "--- SCRIPT DE DESCOBERTA INICIADO ---"})
    devices = run_full_discovery(save_per_interface=True)
    if devices:
        logger.info({"evento": "Execução finalizada com sucesso", "total": len(devices)})
    else:
        logger.info({"evento": "Nenhum dispositivo encontrado ou falha na execução."})
    logger.info({"evento": "--- FIM ---"})
