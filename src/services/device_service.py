# src/services/device_service.py
import logging
from typing import Optional, Dict, Any, List
from netaddr import EUI
from src.utils.root.root import get_project_root
from src.repositories.json_repo import carregar_arquivo, salvar_arquivo
from src.models.Device import Device
from src.utils.root.paths import DEVICES_FILE, CLPS_FILE
import os

PROJECT_ROOT = get_project_root()


# Carrega inicial
_clps_data: List[Dict[str, Any]] = carregar_arquivo(CLPS_FILE)
_others_data: List[Dict[str, Any]] = carregar_arquivo(DEVICES_FILE)

def buscar_todos() -> List[Dict[str, Any]]:
    return list(_clps_data)  # cópia superficial

def buscar_por_ip(ip_procurado: str) -> Optional[Dict[str, Any]]:
    for clp in _clps_data:
        if clp.get("ip") == ip_procurado:
            return clp
    for dev in _others_data:
        if dev.get("ip") == ip_procurado:
            return dev
    return None

def _remover_por_ip_de_lista(ip: str, lista: List[Dict[str, Any]]) -> None:
    idx = next((i for i, e in enumerate(lista) if e.get("ip") == ip), None)
    if idx is not None:
        lista.pop(idx)

def salvar_clps() -> None:
    salvar_arquivo(CLPS_FILE, _clps_data)

def salvar_others() -> None:
    salvar_arquivo(DEVICES_FILE, _others_data)

def criar_dispositivo(dados: dict, grupo: str = "Sem Grupo") -> Dict[str, Any]:
    ip = dados.get("ip")
    mac = dados.get("mac")
    subnet = dados.get("subnet", "Desconhecida")
    portas = dados.get("portas", []) or []

    if not ip:
        logging.warning("[WARN] criar_dispositivo chamado sem IP válido.")
        return {}

    existente = buscar_por_ip(ip)
    if existente:
        logging.info(f"[INFO] Atualizando dispositivo existente: {ip}")
        portas_existentes = set(existente.get("portas", []))
        portas_existentes.update(portas)
        existente["portas"] = sorted(list(portas_existentes))
        existente.setdefault("logs", []).append({
            "acao": "Atualizacao",
            "detalhes": f"Portas atualizadas: {portas}",
            "data": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        if existente.get("tipo") == "CLP":
            salvar_clps()
        else:
            salvar_others()
        return existente

    # determina fabricante via MAC (se fornecida)
    fabricante = "Desconhecido"
    if mac:
        try:
            fabricante = str(EUI(mac).oui.registration().org)
        except Exception:
            fabricante = "Desconhecido"

    tipo = "Desconhecido"
    fabricante_l = (fabricante or "").lower()
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

    dispositivo = Device(
        ip=ip,
        mac=mac or "",
        subnet=subnet,
        portas=sorted(list(set(portas))),
        nome=nome,
        tipo=tipo,
        grupo=grupo,
    ).to_dict()

    dispositivo.setdefault("logs", []).append({
        "acao": "Enriquecimento",
        "detalhes": f"Dispositivo identificado como {tipo}, fabricante: {fabricante}",
        "data": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    if tipo == "CLP":
        _clps_data.append(dispositivo)
        salvar_clps()
        logging.info(f"[INFO] Novo CLP criado e salvo em {CLPS_FILE}: {ip}")
    else:
        _others_data.append(dispositivo)
        salvar_others()
        logging.info(f"[INFO] Novo dispositivo (não-CLP) criado e salvo em {DEVICES_FILE}: {ip}")

    return dispositivo

def listar_clps() -> List[Dict[str, Any]]:
    return list(_clps_data)

def listar_devices() -> List[Dict[str, Any]]:
    return list(_others_data)
