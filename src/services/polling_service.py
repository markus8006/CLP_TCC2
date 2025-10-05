# src/services/polling_service.py
import os
import time
import threading
import copy
from typing import Dict, Any, List, Optional, Tuple

from src.adapters.modbus_adapter import ModbusAdapter
from src.repositories.clp_repository import CLPRepository
from src.services.clp_service import CLPService
from src.utils.log.log import setup_logger
from src.models import CLPConfigRegistrador # Importa o modelo de configuração

LOG = setup_logger()

MODBUS_MAX_REGS = 125

# (As funções build_batches e add_log_in_memory permanecem iguais)
def build_batches(registers: List[Dict[str, Any]]) -> List[Tuple[str, int, int, List[Dict[str, Any]]]]:
    # ... código sem alterações ...
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for r in registers:
        rtype = r.get("type", "holding")
        by_type.setdefault(rtype, []).append(r)

    batches: List[Tuple[str, int, int, List[Dict[str, Any]]]] = []
    for rtype, regs in by_type.items():
        regs_sorted = sorted(regs, key=lambda x: int(x["address"]))
        i = 0
        while i < len(regs_sorted):
            start = int(regs_sorted[i]["address"])
            end = start + int(regs_sorted[i].get("count", 1)) - 1
            group = [regs_sorted[i]]
            j = i + 1
            while j < len(regs_sorted):
                cand = regs_sorted[j]
                cand_start = int(cand["address"])
                cand_end = cand_start + int(cand.get("count", 1)) - 1
                new_count = max(end, cand_end) - start + 1
                if cand_start <= end + 1 and new_count <= MODBUS_MAX_REGS:
                    end = max(end, cand_end)
                    group.append(cand)
                    j += 1
                else:
                    break
            count = end - start + 1
            batches.append((rtype, start, count, group))
            i = j
    return batches

def add_log_in_memory(clp: dict, entry: str, max_logs: int = 200):
    # ... código sem alterações ...
    if clp is None:
        return
    logs = clp.setdefault("logs", [])
    if logs and logs[-1] == entry:
        return
    logs.append(entry)
    if len(logs) > max_logs:
        del logs[0]

class CLPPoller(threading.Thread):
    def __init__(self, clp: Dict[str, Any], adapter: ModbusAdapter, cache: Dict[str, Any],
                 stop_event: threading.Event, app=None):
        super().__init__(daemon=True, name=f"CLPPoller-{clp.get('ip')}")
        self.clp = clp
        self.adapter = adapter
        self.cache = cache
        self.stop_event = stop_event
        self.app = app
        self._last_read: Dict[str, float] = {}
        self._lock = threading.RLock()

    def _load_registers_config(self) -> List[Dict[str, Any]]:
        """
        Carrega a configuração dos registradores a partir do banco de dados.
        """
        if not self.app or not self.clp.get("id"):
            LOG.warning("Polling p/ %s: App Context ou ID do CLP indisponível para carregar configs do DB.", self.clp.get("ip"))
            return []

        with self.app.app_context():
            try:
                configs_orm = CLPConfigRegistrador.query.filter_by(
                    clp_id=self.clp["id"], 
                    ativo=True
                ).all()

                if not configs_orm:
                    LOG.debug("Nenhuma config de registrador ativa no DB para CLP %s", self.clp.get("ip"))
                    return []

                register_list = [{
                    "name": config.nome_variavel,
                    "address": config.endereco_inicial,
                    "count": config.quantidade,
                    # O poller usa segundos, o DB armazena em milissegundos
                    "interval": (config.intervalo_leitura or 1000) / 1000.0,
                    "type": config.tipo or "holding" 
                } for config in configs_orm]
                
                LOG.debug("Carregados %d registradores do DB para CLP %s", len(register_list), self.clp.get("ip"))
                return register_list

            except Exception as e:
                LOG.exception("Erro ao carregar configs do DB para CLP %s: %s", self.clp.get("ip"), e)
                return []
    
    # --- O resto da classe CLPPoller (run, _should_read, etc.) permanece o mesmo ---
    # ...
    def _should_read(self, reg: Dict[str, Any], now: float) -> bool:
        interval = float(reg.get("interval") or self.clp.get("default_interval") or 5)
        last = self._last_read.get(reg["name"], 0)
        return (now - last) >= interval

    def _persist_register_value(self, reg_name: str, value: Any, ts: float):
        # Esta função pode ser melhorada no futuro para salvar no HistóricoLeitura
        pass

    def run(self):
        ip = self.clp.get("ip")
        LOG.info("CLPPoller[%s] iniciado", ip)
        adapter = self.adapter
        try:
            adapter.connect(self.clp)
        except Exception:
            LOG.debug("Falha inicial de connect para %s", ip)

        while not self.stop_event.is_set():
            now = time.time()
            registers = self._load_registers_config()
            if not registers:
                time.sleep(5.0) # Espera mais se não há nada para fazer
                continue

            batches = build_batches(registers)
            for rtype, start, count, group in batches:
                needs_read = any(self._should_read(reg, now) for reg in group)
                if not needs_read:
                    continue

                if not adapter.connect(self.clp):
                    LOG.warning("CLPPoller[%s] não conectou; pulando batch %s:%s", ip, start, count)
                    add_log_in_memory(self.clp, f"connect failed on batch {start}:{count}")
                    time.sleep(2.0) # Pausa antes de tentar o próximo batch
                    continue

                try:
                    raw = adapter.read_tag(self.clp, start, count)
                except Exception as e:
                    LOG.exception("CLPPoller read_tag exception %s %s", ip, e)
                    raw = None

                if not raw:
                    LOG.debug("CLPPoller[%s] read retornou vazio em %s:%s", ip, start, count)
                    add_log_in_memory(self.clp, f"read empty {start}:{count}")
                    continue

                for reg in group:
                    name = reg["name"]
                    addr = int(reg["address"])
                    cnt = int(reg.get("count", 1))
                    offset = addr - start
                    try:
                        segment = raw[offset: offset + cnt]
                        value = segment[0] if len(segment) == 1 else segment
                        ts = time.time()
                        
                        with self._lock:
                            self.cache.setdefault(ip, {})
                            self.cache[ip][name] = {"value": value, "timestamp": ts, "address": addr}
                        
                        self._persist_register_value(name, value, ts)
                        self._last_read[name] = now
                    except IndexError:
                        LOG.warning("Erro de índice ao processar registrador %s para CLP %s", name, ip)
                    except Exception:
                        LOG.exception("Erro ao separar segmento para %s %s", ip, name)
                
                if self.stop_event.is_set():
                    break
                time.sleep(0.05)

            time.sleep(0.5)

        try:
            adapter.disconnect(self.clp)
        except Exception:
            pass
        LOG.info("CLPPoller[%s] finalizado", ip)


class PollingService:
    def __init__(self, adapter: Optional[ModbusAdapter] = None):
        self.adapter = adapter or ModbusAdapter()
        self._pollers: Dict[str, CLPPoller] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._global_lock = threading.RLock()
        self.app = None

    def set_app(self, app):
        self.app = app

    def start_poll_for(self, clp: Dict[str, Any]) -> bool:
        ip = clp.get("ip")
        if not ip:
            return False
        with self._global_lock:
            if ip in self._pollers:
                return True
            stop_event = threading.Event()
            poller = CLPPoller(
                clp=clp, 
                adapter=self.adapter, 
                cache=self._cache,
                stop_event=stop_event, 
                app=self.app
            )
            self._stop_events[ip] = stop_event
            self._pollers[ip] = poller
            poller.start()
            LOG.info("PollingService: iniciado poller para %s", ip)
        return True

    def stop_poll_for(self, ip: str) -> bool:
        with self._global_lock:
            if ip not in self._pollers:
                return False
            self._stop_events[ip].set()
            self._pollers[ip].join(timeout=5)
            self._pollers.pop(ip, None)
            self._stop_events.pop(ip, None)
            LOG.info("PollingService: parado poller para %s", ip)
        return True

    def start_all_from_db(self):
        clps_orm = CLPRepository.get_all()
        clps_ativos = [CLPService._serialize_clp(clp) for clp in clps_orm if clp.ativo]
        for clp_dict in clps_ativos:
            self.start_poll_for(clp_dict)

    def stop_all(self):
        for ip in list(self._pollers.keys()):
            self.stop_poll_for(ip)

    def get_cache(self) -> Dict[str, Dict[str, Any]]:
        with self._global_lock:
            return copy.deepcopy(self._cache)

    def is_running(self, ip: str) -> bool:
        return ip in self._pollers

polling_service = PollingService()