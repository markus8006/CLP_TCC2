# src/utils/network/discovery.py
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

# imports do seu projeto
try:
    from src.utils.network.portas import escanear_portas  # opcional, fallback
except Exception:
    escanear_portas = None

from src.utils.permissao.permissao import verificar_permissoes
from src.utils.log.log import setup_logger
from src.utils.root.paths import DISCOVERY_FILE

logger = setup_logger()

# -----------------------
# CONFIGURAÇÕES
# -----------------------
COMMON_PLC_PORTS: List[int] = [502, 102, 44818, 1911, 161, 4840]  # Modbus, S7, EtherNet/IP, Rockwell, SNMP, OPC-UA
DEFAULT_PASSIVE_TIMEOUT = 30
DEFAULT_ARP_TIMEOUT = 2
DEFAULT_ICMP_TIMEOUT = 1
DEFAULT_TCP_TIMEOUT = 0.5
MAX_WORKERS = 12
USE_NMAP_FOR_FULL_PORT_SCAN = True  # controlar se nmap será usado
NMAP_TIMEOUT_PER_HOST = 300  # segundos, ajustar conforme necessário


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
        # tenta ip neigh (Linux)
        with os.popen("ip neigh") as p:
            out = p.read().strip().splitlines()
        for line in out:
            parts = line.split()
            if len(parts) >= 5:
                ip = parts[0]
                if "lladdr" in parts:
                    idx = parts.index("lladdr") + 1
                    mac = parts[idx] if idx < len(parts) else None
                else:
                    mac = parts[4] if len(parts) > 4 else None
                if mac:
                    arp_map[ip] = mac
    except Exception:
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
# NMAP wrapper
# -----------------------
def _nmap_available() -> bool:
    return shutil.which("nmap") is not None


def nmap_scan_host(
    ip: str,
    all_ports: bool = True,
    extra_args: Optional[List[str]] = None,
    use_syn_scan_if_root: bool = True,
    timeout: int = NMAP_TIMEOUT_PER_HOST,
) -> Dict[int, Dict[str, Any]]:
    """
    Executa nmap para o host `ip` e retorna um dict {porta: {state, proto, service, product, version}}.
    Usa -oX - (XML para stdout) e faz parse.
    """
    result: Dict[int, Dict[str, Any]] = {}

    if not _nmap_available():
        logger.warning({"evento": "nmap não encontrado no sistema; pulando nmap_scan_host", "ip": ip})
        return result

    cmd: List[str] = ["nmap", "-oX", "-"]

    # scan type
    if use_syn_scan_if_root and os.geteuid() == 0:
        cmd += ["-sS"]
    else:
        cmd += ["-sT"]

    # version detection and speed
    cmd += ["-sV", "--version-intensity", "0", "-T4"]

    # all ports or extra_args
    if all_ports:
        cmd += ["-p-"]
    if extra_args:
        cmd += extra_args

    cmd.append(ip)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        stdout = proc.stdout
        if not stdout:
            return result

        root = ET.fromstring(stdout)
        for host in root.findall("host"):
            ports = host.find("ports")
            if ports is None:
                continue
            for p in ports.findall("port"):
                try:
                    portid = int(p.attrib.get("portid", "-1"))
                    proto = p.attrib.get("protocol")
                    state_node = p.find("state")
                    state = state_node.attrib.get("state") if state_node is not None else "unknown"
                    service_node = p.find("service")
                    service = service_node.attrib.get("name") if service_node is not None else None
                    product = service_node.attrib.get("product") if service_node is not None else None
                    version = service_node.attrib.get("version") if service_node is not None else None

                    result[portid] = {
                        "proto": proto,
                        "state": state,
                        "service": service,
                        "product": product,
                        "version": version,
                    }
                except Exception:
                    continue
    except subprocess.TimeoutExpired:
        logger.warning({"evento": "nmap timeout", "ip": ip})
    except Exception as e:
        logger.error({"evento": "Erro executando nmap", "ip": ip, "detalhes": str(e)})

    return result


# -----------------------
# Passive discovery (sniff)
# -----------------------
def discover_passively(timeout: int = DEFAULT_PASSIVE_TIMEOUT) -> Set[str]:
    """
    Sniff passivamente na(s) interfaces por `timeout` segundos.
    Retorna set de IPs observados.
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

    sniff(store=0, prn=_pkt_handler, timeout=timeout)
    logger.info({"evento": "Descoberta passiva concluída", "total": len(seen_ips)})
    return seen_ips


# -----------------------
# Subnets por interface
# -----------------------
def get_local_subnets() -> Set[Tuple[str, str]]:
    """
    Retorna set de (iface, subnet_cidr). Usa conf.ifaces quando possível,
    senão get_if_list/get_if_addr com heurística /24.
    """
    subnets: Set[Tuple[str, str]] = set()

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
        logger.debug({"evento": "Falha conf.ifaces; usando fallback get_if_list()"})

    if not subnets:
        for iface in get_if_list():
            try:
                ip = get_if_addr(iface)
                if not ip or ip.startswith("127."):
                    continue
                net = str(ipaddress.ip_network(f"{ip}/24", strict=False))
                subnets.add((iface, net))
                logger.info({"evento": "Interface (fallback) detectada", "iface": iface, "ip": ip, "subnet": net})
            except Exception:
                continue

    return subnets


# -----------------------
# ARP scan ativo
# -----------------------
def arp_scan(network_cidr: str, timeout: int = DEFAULT_ARP_TIMEOUT) -> List[Dict[str, str]]:
    """
    Executa ARP scan na faixa (ex: '192.168.1.0/24').
    Retorna list dict {'ip','mac','subnet'}.
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
# ICMP sweep
# -----------------------
def icmp_ping_sweep(ip_list: List[str], timeout: int = DEFAULT_ICMP_TIMEOUT) -> Set[str]:
    """Envia ICMP echo para uma lista de IPs; retorna set de IPs que responderam."""
    alive: Set[str] = set()
    if not ip_list:
        return alive
    try:
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
# TCP probe rápido (connect)
# -----------------------
def tcp_probe(ip: str, ports: List[int], timeout: float = DEFAULT_TCP_TIMEOUT) -> Dict[int, bool]:
    """
    Tenta conexão TCP connect_ex nas portas; retorna dict porta->bool.
    Uso rápido, não substitui nmap para descoberta completa.
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
# Helpers para colapso / merge por MAC
# -----------------------
def _normalize_mac(mac: Optional[str]) -> Optional[str]:
    """Normaliza MAC para formato aa:bb:cc:dd:ee:ff ou retorna None se inválida."""
    if not mac:
        return None
    mac = mac.strip().lower().replace("-", ":")
    mac = re.sub(r'[^0-9a-f:]', '', mac)
    mac = re.sub(r':{2,}', ':', mac)
    if not re.match(r'^([0-9a-f]{2}:){5}[0-9a-f]{2}$', mac):
        return None
    if mac in ("00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"):
        return None
    return mac


def _merge_port_dicts(a: Dict[int, Any], b: Dict[int, Any]) -> Dict[int, Any]:
    """Faz merge simples de dicts de portas:
       - booleans -> OR lógico
       - dicts (nmap) -> merge preferindo 'open'
    """
    if not a:
        return copy.deepcopy(b) if b else {}
    if not b:
        return copy.deepcopy(a)
    out = copy.deepcopy(a)
    for port, val in b.items():
        if port in out:
            aval = out[port]
            if isinstance(aval, bool) and isinstance(val, bool):
                out[port] = aval or val
            elif isinstance(aval, dict) and isinstance(val, dict):
                merged = dict(aval)
                for k, v in val.items():
                    if k == "state":
                        if merged.get("state") != "open":
                            merged["state"] = v
                    else:
                        if v is not None:
                            merged[k] = v
                out[port] = merged
            else:
                out[port] = val or aval
        else:
            out[port] = copy.deepcopy(val)
    return out


def _collapse_devices_by_mac(all_devices: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agrupa/colapsa entries por MAC quando disponível. Para entradas sem MAC usa ip como chave.
    Mantém lista ips_seen em cada dispositivo final para histórico.
    """
    grouped: Dict[str, Dict[str, Any]] = {}

    for ip, entry in all_devices.items():
        mac_raw = entry.get("mac")
        mac = _normalize_mac(mac_raw)
        key = mac if mac else f"ip::{ip}"

        if key not in grouped:
            grouped[key] = copy.deepcopy(entry)
            grouped[key]["ips_seen"] = [ip]
            # garantir mac normalizado quando disponível
            if mac:
                grouped[key]["mac"] = mac
        else:
            target = grouped[key]
            if ip not in target.get("ips_seen", []):
                target.setdefault("ips_seen", []).append(ip)

            # discovered_via
            dv = set(target.get("discovered_via", []) or [])
            dv.update(entry.get("discovered_via", []) or [])
            target["discovered_via"] = list(dv)

            # iface/subnet: preferir valores existentes
            if not target.get("iface") and entry.get("iface"):
                target["iface"] = entry.get("iface")
            if not target.get("subnet") and entry.get("subnet"):
                target["subnet"] = entry.get("subnet")

            # alive_icmp: OR lógico
            target["alive_icmp"] = bool(target.get("alive_icmp") or entry.get("alive_icmp"))

            # portas -> merge
            target["portas"] = _merge_port_dicts(target.get("portas", {}), entry.get("portas", {}))

            # portas_nmap -> merge
            target["portas_nmap"] = _merge_port_dicts(target.get("portas_nmap", {}), entry.get("portas_nmap", {}))

            # portas_detalhadas -> tentar mesclar se dicts
            if not target.get("portas_detalhadas") and entry.get("portas_detalhadas"):
                target["portas_detalhadas"] = entry.get("portas_detalhadas")
            elif isinstance(target.get("portas_detalhadas"), dict) and isinstance(entry.get("portas_detalhadas"), dict):
                merged_det = dict(target["portas_detalhadas"])
                merged_det.update(entry["portas_detalhadas"])
                target["portas_detalhadas"] = merged_det

            # mac: preencher se não existia
            if not target.get("mac") and mac:
                target["mac"] = mac

    # escolher ip representativo e montar lista final
    final_list: List[Dict[str, Any]] = []
    for key, item in grouped.items():
        seen_ips = item.get("ips_seen", [])
        chosen_ip = None

        # preferir IP com alive_icmp True
        if seen_ips:
            for cand in seen_ips:
                orig = all_devices.get(cand)
                if orig and orig.get("alive_icmp"):
                    chosen_ip = cand
                    break

        # senão preferir IP com portas abertas
        if not chosen_ip:
            for cand in seen_ips:
                orig = all_devices.get(cand, {})
                portas = orig.get("portas") or {}
                if any(portas.values()):
                    chosen_ip = cand
                    break

        # senão usar primeiro
        if not chosen_ip and seen_ips:
            chosen_ip = seen_ips[0]

        if chosen_ip and chosen_ip in all_devices:
            src = all_devices[chosen_ip]
            item["ip"] = chosen_ip
            if src.get("iface"):
                item["iface"] = src.get("iface")
            if src.get("subnet"):
                item["subnet"] = src.get("subnet")

        # defensivo: garantir campo ip
        if not item.get("ip") and seen_ips:
            item["ip"] = seen_ips[0]

        final_list.append(item)

    # ordenar por ip
    final_list = _safe_ip_sort(final_list)
    return final_list


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
    use_nmap: bool = USE_NMAP_FOR_FULL_PORT_SCAN,
) -> List[Dict[str, Any]]:
    """
    Pipeline completo:
      1) passive sniff
      2) get local subnets
      3) ARP scan por subnet (paralelo)
      4) preencher com passivos
      5) ICMP sweep (chunks)
      6) TCP probes rápidos (paralelo)
      7) (opcional) nmap -p- por host para descobrir todas portas (paralelo)
      8) (opcional) usar escanear_portas para detalhes
      9) salvar JSON (agrupar por MAC)
    """
    if ports is None:
        ports = COMMON_PLC_PORTS

    if not verificar_permissoes():
        logger.error({"evento": "Permissões insuficientes (discovery)", "detalhes": "Executar como root/adm."})
        return []

    start_ts = time()
    logger.info({"evento": "Começando descoberta completa"})

    # 1) sniff passivo
    passive_ips = discover_passively(timeout=passive_timeout)

    # 2) obter subnets
    iface_subnets = get_local_subnets()
    if not iface_subnets:
        logger.warning({"evento": "Nenhuma interface/sub-rede detectada"})
        return []

    # 3) ARP scan paralelo
    all_devices: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=parallel_workers) as ex:
        futures = {ex.submit(arp_scan, subnet, arp_timeout): (iface, subnet) for iface, subnet in iface_subnets}
        for fut in as_completed(futures):
            iface, subnet = futures[fut]
            try:
                devices = fut.result()
            except Exception as e:
                logger.debug({"evento": "Erro em ARP future", "iface": iface, "subnet": subnet, "detalhes": str(e)})
                devices = []
            for d in devices:
                ip = d["ip"]
                if ip not in all_devices:
                    all_devices[ip] = {
                        "ip": ip,
                        "mac": d.get("mac"),
                        "subnet": d.get("subnet"),
                        "iface": iface,
                        "discovered_via": ["arp"],
                        "alive_icmp": False,
                        "portas": {},
                    }
                else:
                    if "arp" not in all_devices[ip]["discovered_via"]:
                        all_devices[ip]["discovered_via"].append("arp")
                    if not all_devices[ip].get("mac"):
                        all_devices[ip]["mac"] = d.get("mac")
                    if not all_devices[ip].get("iface"):
                        all_devices[ip]["iface"] = iface

    # 4) incluir IPs passivos que não apareceram no ARP
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

    # 5) associar iface/subnet por matching de rede
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

    # 6) complementar com ARP cache
    try:
        arp_cache = _read_arp_cache()
        for ip, mac in arp_cache.items():
            if ip in all_devices and not all_devices[ip].get("mac"):
                all_devices[ip]["mac"] = mac
    except Exception:
        arp_cache = {}

    # 7) ICMP sweep em chunks
    ips_list = list(all_devices.keys())
    alive_ips: Set[str] = set()
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

    # 8) tcp_probe rápido em paralelo (opcional antes do nmap)
    with ThreadPoolExecutor(max_workers=parallel_workers) as ex:
        future_map = {ex.submit(tcp_probe, ip, ports, tcp_timeout): ip for ip in all_devices.keys()}
        for fut in as_completed(future_map):
            ip = future_map[fut]
            try:
                res = fut.result()
                all_devices[ip]["portas"] = res
                if any(res.values()) and "tcp" not in all_devices[ip]["discovered_via"]:
                    all_devices[ip]["discovered_via"].append("tcp")
            except Exception as e:
                logger.debug({"evento": "Erro tcp_probe", "ip": ip, "detalhes": str(e)})

    # 9) Nmap (varredura completa de portas) - paralelo por host (pode ser lento)
    if use_nmap and _nmap_available():
        logger.info({"evento": "Usando nmap para varredura completa de portas (pode demorar)"})
        with ThreadPoolExecutor(max_workers=parallel_workers) as ex:
            future_map = {ex.submit(nmap_scan_host, ip, True, None, True, NMAP_TIMEOUT_PER_HOST): ip for ip in all_devices.keys()}
            for fut in as_completed(future_map):
                ip = future_map[fut]
                try:
                    nmap_res = fut.result()
                    all_devices[ip]["portas_nmap"] = nmap_res
                    any_open = any(v.get("state") == "open" for v in nmap_res.values())
                    if any_open and "nmap" not in all_devices[ip]["discovered_via"]:
                        all_devices[ip]["discovered_via"].append("nmap")
                except Exception as e:
                    logger.debug({"evento": "Erro nmap_scan_host", "ip": ip, "detalhes": str(e)})
    else:
        if use_nmap:
            logger.warning({"evento": "nmap configurado mas não instalado; pulando nmap step"})

    # 10) fallback: escanear_portas (se disponível) para hosts com portas abertas detectadas
    if escanear_portas:
        try:
            with ThreadPoolExecutor(max_workers=parallel_workers) as ex:
                futures = {}
                for ip, entry in all_devices.items():
                    call = False
                    if entry.get("portas") and any(entry["portas"].values()):
                        call = True
                    if entry.get("portas_nmap") and any(v.get("state") == "open" for v in entry["portas_nmap"].values()):
                        call = True
                    if call:
                        futures[ex.submit(escanear_portas, ip)] = ip
                for fut in as_completed(futures):
                    ip = futures[fut]
                    try:
                        portas_detalhadas = fut.result()
                        all_devices[ip]["portas_detalhadas"] = portas_detalhadas
                    except Exception as e:
                        logger.debug({"evento": "Erro escanear_portas future", "ip": ip, "detalhes": str(e)})
        except Exception:
            pass

    # resultado final: colapsar por mac e salvar
    devices_final = _collapse_devices_by_mac(all_devices)

    elapsed = time() - start_ts
    logger.info({"evento": "Descoberta completa", "total": len(devices_final), "tempo_segundos": elapsed})

    # gravação atômica do arquivo DISCOVERY_FILE (usa temp + replace)
    try:
        dirpath = os.path.dirname(DISCOVERY_FILE) or "."
        os.makedirs(dirpath, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", delete=False, dir=dirpath, encoding="utf-8") as tf:
            json.dump(devices_final, tf, indent=2, ensure_ascii=False)
            tmpname = tf.name
        os.replace(tmpname, DISCOVERY_FILE)
        logger.info({"evento": "Resultados salvos", "arquivo": DISCOVERY_FILE})
    except Exception as e:
        logger.error({"evento": "Falha ao salvar resultados", "detalhes": str(e)})

    # salvar por interface opcional (também atômico)
    if save_per_interface:
        by_iface: Dict[str, List[Dict[str, Any]]] = {}
        for d in devices_final:
            iface = d.get("iface") or "unknown"
            by_iface.setdefault(iface, []).append(d)
        for iface, lst in by_iface.items():
            safe_base = DISCOVERY_FILE.rstrip(".json")
            fname = f"{safe_base}_{iface}.json"
            try:
                dirpath = os.path.dirname(fname) or "."
                os.makedirs(dirpath, exist_ok=True)
                with tempfile.NamedTemporaryFile("w", delete=False, dir=dirpath, encoding="utf-8") as tf:
                    json.dump(lst, tf, indent=2, ensure_ascii=False)
                    tmpname = tf.name
                os.replace(tmpname, fname)
                logger.info({"evento": "Salvo por interface", "iface": iface, "arquivo": fname})
            except Exception as e:
                logger.warning({"evento": "Erro salvando por interface", "iface": iface, "detalhes": str(e)})

    return devices_final


# -----------------------
# helper para background
# -----------------------
def discovery_background_once() -> None:
    logger.info({"evento": "Iniciando discovery_background_once"})
    try:
        run_full_discovery()
    except Exception as e:
        logger.error({"evento": "Erro discovery_background_once", "detalhes": str(e)})


# -----------------------
# executável
# -----------------------
if __name__ == "__main__":
    logger.info({"evento": "--- SCRIPT DE DESCOBERTA INICIADO ---"})
    devices = run_full_discovery(save_per_interface=True, use_nmap=USE_NMAP_FOR_FULL_PORT_SCAN)
    if devices:
        logger.info({"evento": "Execução finalizada com sucesso", "total": len(devices)}))
    else:
        logger.info({"evento": "Nenhum dispositivo encontrado ou falha na execução."})
    logger.info({"evento": "--- FIM ---"})
