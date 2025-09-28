# src/services/device_service.py
import logging
from typing import Optional, Dict, Any, List, Union, Iterable
from datetime import datetime
from netaddr import EUI
from src.utils.root.root import get_project_root
from src.repositories.json_repo import carregar_arquivo, salvar_arquivo
from src.models.Device import Device
from src.utils.root.paths import DEVICES_FILE, CLPS_FILE

PROJECT_ROOT = get_project_root()
logger = logging.getLogger(__name__)

# Carrega inicial (garante lista vazia se arquivo não existir/retornar None)
_clps_data: List[Dict[str, Any]] = carregar_arquivo(CLPS_FILE) or []
_others_data: List[Dict[str, Any]] = carregar_arquivo(DEVICES_FILE) or []


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def buscar_todos() -> List[Dict[str, Any]]:
    """Retorna uma cópia superficial da lista de CLPs (compatibilidade com código existente)."""
    return list(_clps_data)


def buscar_por_ip(ip_procurado: str) -> Optional[Dict[str, Any]]:
    """Procura por IP nas listas de CLP e outros dispositivos."""
    for clp in _clps_data:
        if clp.get("ip") == ip_procurado:
            return clp
    for dev in _others_data:
        if dev.get("ip") == ip_procurado:
            return dev
    return None


def _remover_por_ip_de_lista(ip: str, lista: List[Dict[str, Any]]) -> None: # pyright: ignore[reportUnusedFunction]
    """Remove o primeiro elemento com o IP fornecido da lista (mutável)."""
    idx = next((i for i, e in enumerate(lista) if e.get("ip") == ip), None)
    if idx is not None:
        lista.pop(idx)


def salvar_clps() -> None:
    salvar_arquivo(CLPS_FILE, _clps_data)


def salvar_others() -> None:
    salvar_arquivo(DEVICES_FILE, _others_data)


def _to_int_list(iterable: Optional[Iterable[Any]]) -> List[int]:
    """Converte uma sequência de valores possivelmente string/int em lista de ints (ignora inválidos)."""
    if not iterable:
        return []
    out: List[int] = []
    for v in iterable:
        try:
            out.append(int(v))
        except Exception:
            continue
    return sorted(list(set(out)))


def criar_dispositivo(dados: Dict[str, Any], grupo: str = "Sem Grupo", Manual=False) -> Dict[str, Any]:
    """
    Cria um dispositivo (ou atualiza portas se já existir). Não altera outras listas/estruturas externas.
    """
    ip = dados.get("ip")
    mac = dados.get("mac")
    subnet = dados.get("subnet", "Desconhecida")
    portas_raw : List[int] = dados.get("portas", []) or []
    portas = _to_int_list(portas_raw)
    protocolo = "modbus"

    if not ip or not isinstance(ip, str):
        logger.warning("[WARN] criar_dispositivo chamado sem IP válido.")
        return {}

    existente = buscar_por_ip(ip)
    if existente:
        logger.info(f"[INFO] Atualizando dispositivo existente: {ip}")
        portas_existentes = set(_to_int_list(existente.get("portas", [])))
        portas_existentes.update(portas)
        existente["portas"] = sorted(list(portas_existentes))
        existente.setdefault("logs", []).append({
            "acao": "Atualizacao",
            "detalhes": f"Portas atualizadas: {portas}",
            "data": _now_str()
        })
        if existente.get("tipo") == "CLP":
            salvar_clps()
        else:
            salvar_others()
        return existente

    # determina fabricante via MAC (se fornecida)
    fabricante = "Desconhecido"
    if mac and isinstance(mac, str):
        try:
            reg = EUI(mac).oui.registration()
            # registration pode ser objeto ou dict dependendo da versão; tente atributos comuns
            fabricante = ( # pyright: ignore[reportUnknownVariableType]
                getattr(reg, "org", None)
                or getattr(reg, "company", None)
                or (reg.get("org") if isinstance(reg, dict) and "org" in reg else None) # type: ignore
                or str(reg)
            )
            fabricante = fabricante or "Desconhecido" # pyright: ignore[reportUnknownVariableType]
        except Exception:
            fabricante = "Desconhecido"

    # heurística para tipo
    tipo = "Desconhecido"
    fabricante_l : str = (fabricante or "").lower() # type: ignore
    if fabricante_l.startswith(("siemens", "rockwell", "schneider", "mitsubishi")): # type: ignore
        tipo = "CLP"
    elif any(p in portas for p in (5000, 5357)):
        tipo = "Computador"
    elif 22 in portas:
        tipo = "Servidor ou Dispositivo IoT"
    elif 80 in portas or 443 in portas:
        tipo = "Smartphone / Tablet / Web Device"
    elif 554 in portas or 8554 in portas:
        tipo = "Câmera IP"
    elif Manual:
        tipo = "CLP"

    nome = f"{tipo}_{ip}" if tipo != "Desconhecido" else f"Desconhecido_{ip}"

    dispositivo = Device(
        ip=ip,
        mac=mac or "",
        subnet=subnet,
        portas=sorted(list(set(portas))),
        nome=nome,
        tipo=tipo,
        grupo=grupo,
        protocolo=protocolo
    ).to_dict()

    dispositivo.setdefault("logs", []).append({
        "acao": "Enriquecimento",
        "detalhes": f"Dispositivo identificado como {tipo}, fabricante: {fabricante}",
        "data": _now_str()
    })

    if tipo == "CLP":
        _clps_data.append(dispositivo)
        salvar_clps()
        logger.info(f"[INFO] Novo CLP criado e salvo em {CLPS_FILE}: {ip}")
    else:
        _others_data.append(dispositivo)
        salvar_others()
        logger.info(f"[INFO] Novo dispositivo (não-CLP) criado e salvo em {DEVICES_FILE}: {ip}")

    return dispositivo


def listar_clps() -> List[Dict[str, Any]]:
    return list(_clps_data)


def listar_devices() -> List[Dict[str, Any]]:
    return list(_others_data)


def atualizar_clp(json_antigo: Union[Dict[str, Any], str], json_novo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Atualiza um CLP existente.
    Aceita `json_antigo` como dict OU como string contendo o IP (compatibilidade).
    Faz merge inteligente de 'logs', 'portas', 'tags' e 'metadata'. Substitui outros campos.
    """
    # permite receber ip diretamente (compatibilidade com chamadas erradas)
    if isinstance(json_antigo, str):
        ip = json_antigo
    elif isinstance(json_antigo, dict): # type: ignore
        ip = json_antigo.get("ip")
    else:
        ip = None

    if not ip:
        logging.warning("[WARN] atualizar_clp chamado sem IP válido no JSON antigo.")
        return None

    # Busca CLP correspondente
    clp = next((c for c in _clps_data if c.get("ip") == ip), None)
    if not clp:
        logging.warning(f"[WARN] Nenhum CLP encontrado com IP {ip}.")
        return None

    # Atualiza campos do CLP
    for key, value in (json_novo or {}).items():
        if key == "logs":
            if isinstance(value, list):
                clp.setdefault("logs", []).extend(value)
            elif isinstance(value, str):
                clp.setdefault("logs", []).append(value)
            else:
                # ignora tipos estranhos
                continue
        elif key == "portas":
            novas_portas = _to_int_list(value)
            portas_existentes = set(_to_int_list(clp.get("portas", [])))
            portas_existentes.update(novas_portas)
            clp["portas"] = sorted(list(portas_existentes))
        elif key == "tags":
            if isinstance(value, list):
                tags_existentes = set(clp.get("tags", []))
                tags_existentes.update([str(t) for t in value]) # type: ignore
                clp["tags"] = sorted(list(tags_existentes))
            elif isinstance(value, str):
                parts = [t.strip() for t in value.split(",") if t.strip()]
                tags_existentes = set(clp.get("tags", []))
                tags_existentes.update(parts)
                clp["tags"] = sorted(list(tags_existentes))
        elif key == "metadata":
            if isinstance(value, dict):
                clp.setdefault("metadata", {}).update(value)
            else:
                # ignora se metadata não for dict
                continue
        else:
            # substitui valor simples
            clp[key] = value

    # adiciona log automático
    clp.setdefault("logs", []).append({
        "acao": "Atualizacao",
        "detalhes": f"Dispositivo atualizado com novos dados: {list((json_novo or {}).keys())}",
        "data": _now_str()
    })

    salvar_clps()
    logging.info(f"[INFO] CLP {ip} atualizado com sucesso.")
    return clp
