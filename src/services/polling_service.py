# src/services/polling_service.py
import os
import time
import threading
import yaml
import copy
from typing import Dict, Any, List, Optional, Tuple

from src.adapters.modbus_adapter import ModbusAdapter
from src.controllers.clp_controller import ClpController
from src.utils.log.log import setup_logger

LOG = setup_logger()

MODBUS_MAX_REGS = 125  # limite por request (função 3/4)

# path YAML fallback
DEFAULT_YAML_PATH = os.path.join("src", "data", "plc_registers.yaml")


# ---------------------------------------------------
# util: montar batches simples de leituras contíguas
# ---------------------------------------------------
def build_batches(registers: List[Dict[str, Any]]) -> List[Tuple[str, int, int, List[Dict[str, Any]]]]:
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


# ---------------------------------------------------
# helper para adicionar log no objeto clp (em memória)
# ---------------------------------------------------
def add_log_in_memory(clp: dict, entry: str, max_logs: int = 200):
    if clp is None:
        return
    logs = clp.setdefault("logs", [])
    if logs and logs[-1] == entry:
        return
    logs.append(entry)
    if len(logs) > max_logs:
        del logs[0]


# ---------------------------------------------------
# Poller de um CLP (thread)
# ---------------------------------------------------
class CLPPoller(threading.Thread):
    def __init__(self, clp: Dict[str, Any], adapter: ModbusAdapter, cache: Dict[str, Any],
                 stop_event: threading.Event, yaml_path: Optional[str] = None, app=None):
        super().__init__(daemon=True, name=f"CLPPoller-{clp.get('ip')}")
        self.clp = clp
        self.adapter = adapter
        self.cache = cache
        self.stop_event = stop_event
        self._last_read: Dict[str, float] = {}
        self._lock = threading.RLock()
        self.yaml_path = yaml_path or DEFAULT_YAML_PATH
        self.app = app  # opcional, setado via PollingService.set_app(app) antes de persistir DB

    def _load_registers_config(self) -> List[Dict[str, Any]]:
        regs = self.clp.get("registers")
        if regs and isinstance(regs, list):
            return regs

        try:
            if not os.path.exists(self.yaml_path):
                LOG.debug("plc_registers.yaml não encontrado; nenhum registro configurado para %s", self.clp.get("ip"))
                return []
            with open(self.yaml_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            # suportar dois formatos: mapping ip -> list OR antigo formato { devices: [...] }
            if isinstance(cfg, dict):
                # caso top-level seja map ip->regs
                if self.clp.get("ip") in cfg:
                    return cfg.get(self.clp.get("ip")) or []
                # caso top-level seja { devices: [...] }
                devices = cfg.get("devices", [])
                for d in devices:
                    if d.get("host") == self.clp.get("ip") or d.get("name") == self.clp.get("nome"):
                        return d.get("registers", []) or []
        except FileNotFoundError:
            LOG.debug("plc_registers.yaml não encontrado; nenhum registro configurado para %s", self.clp.get("ip"))
        except Exception as e:
            LOG.exception("Erro lendo plc_registers.yaml: %s", e)
        return []

    def _should_read(self, reg: Dict[str, Any], now: float) -> bool:
        interval = int(reg.get("interval") or self.clp.get("default_interval") or 5)
        last = self._last_read.get(reg["name"], 0)
        return (now - last) >= interval

    def _persist_register_value(self, reg_name: str, value: Any, ts: float):
        """
        Persistência:
         - atualiza ClpController (in-memory/padrão do seu app)
         - se app estiver disponível, grava RegisterValue no DB (opcional)
        """
        # 1) atualiza in-memory via controller (evita circular imports diretos de models)
        try:
            clp_current = ClpController.obter_por_ip(self.clp.get("ip"))
            if clp_current:
                clp_current.setdefault("registers_values", {})
                clp_current["registers_values"][reg_name] = {"value": value, "timestamp": ts}
                # adiciona log simples
                add_log_in_memory(clp_current, f"read {reg_name}={value}")
                # salva via controller (se implementar persistência, o controller cuida)
                try:
                    ClpController.editar_clp(clp_current, clp_current)
                except Exception:
                    # se editar_clp tiver assinatura diferente, tente editar com ip/upsert ou ignore
                    LOG.debug("ClpController.editar_clp falhou ao persistir register in-memory (ignorado).")
        except Exception:
            LOG.exception("Erro atualizando ClpController in-memory para %s", self.clp.get("ip"))

        # 2) persistir no DB (opcional) se self.app for setada e models existirem
        if self.app:
            try:
                # import dentro do contexto para evitar import circular em tempo de import do módulo
                from src.views import db  # seu SQLAlchemy instance
                # modelo RegisterValue pode estar em src.models.registers ou outro path; tentamos import seguro
                try:
                    from src.models.Registers import RegisterValue  # sob conventions lowercase
                except Exception:
                    try:
                        from src.models.Registers import RegisterValue  # fallback possible path
                    except Exception:
                        RegisterValue = None

                if RegisterValue:
                    with self.app.app_context():
                        rv = RegisterValue(
                            clp_ip=self.clp.get("ip"),
                            reg_name=reg_name,
                            value=str(value),
                            timestamp=ts
                        )
                        db.session.add(rv)
                        db.session.commit()
                        LOG.debug("RegisterValue salvo no DB: %s %s=%s", self.clp.get("ip"), reg_name, value)
                else:
                    LOG.debug("Modelo RegisterValue não encontrado; pulando persistência DB.")
            except Exception:
                try:
                    with self.app.app_context():
                        db.session.rollback()
                except Exception:
                    pass
                LOG.exception("Erro salvando RegisterValue no DB para %s", self.clp.get("ip"))

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
                time.sleep(2.0)
                continue

            batches = build_batches(registers)
            for rtype, start, count, group in batches:
                needs = False
                for reg in group:
                    if self._should_read(reg, now):
                        needs = True
                        break
                if not needs:
                    continue

                if not adapter.connect(self.clp):
                    LOG.warning("CLPPoller[%s] não conectou; pulando batch %s:%s", ip, start, count)
                    add_log_in_memory(self.clp, f"connect failed on batch {start}:{count}")
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
                    except Exception:
                        LOG.exception("Erro ao separar segmento para %s %s", ip, name)
                        segment = None

                    if not segment:
                        continue

                    value = segment[0] if len(segment) == 1 else segment
                    ts = time.time()
                    # atualizar cache local
                    with self._lock:
                        self.cache.setdefault(self.clp.get("ip"), {})
                        self.cache[self.clp.get("ip")][name] = {"value": value, "timestamp": ts, "address": addr}

                    # persistir via controlador e opcionalmente DB
                    self._persist_register_value(name, value, ts)
                    self._last_read[name] = now

                if self.stop_event.is_set():
                    break
                time.sleep(0.05)

            time.sleep(0.5)

        try:
            adapter.disconnect(self.clp)
        except Exception:
            pass
        LOG.info("CLPPoller[%s] finalizado", ip)


# ---------------------------------------------------
# Serviço que gerencia pollers
# ---------------------------------------------------
class PollingService:
    def __init__(self, adapter: Optional[ModbusAdapter] = None, yaml_path: Optional[str] = None):
        self.adapter = adapter or ModbusAdapter()
        self._pollers: Dict[str, CLPPoller] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._global_lock = threading.RLock()
        self.yaml_path = yaml_path or DEFAULT_YAML_PATH
        self.app = None  # set by set_app

    def set_app(self, app):
        """Anexe o Flask app para permitir persistência em DB a partir das threads."""
        self.app = app

    def start_poll_for(self, clp: Dict[str, Any]) -> bool:
        ip = clp.get("ip")
        if not ip:
            return False
        with self._global_lock:
            if ip in self._pollers:
                LOG.info("PollingService: poller já ativo para %s", ip)
                return True
            stop_event = threading.Event()
            poller = CLPPoller(clp=clp, adapter=self.adapter, cache=self._cache,
                               stop_event=stop_event, yaml_path=self.yaml_path, app=self.app)
            self._stop_events[ip] = stop_event
            self._pollers[ip] = poller
            poller.start()
            LOG.info("PollingService: iniciado poller para %s", ip)
        return True

    def stop_poll_for(self, ip: str) -> bool:
        with self._global_lock:
            poller = self._pollers.get(ip)
            if not poller:
                return False
            ev = self._stop_events.get(ip)
            if ev:
                ev.set()
            poller.join(timeout=5)
            self._pollers.pop(ip, None)
            self._stop_events.pop(ip, None)
            LOG.info("PollingService: parado poller para %s", ip)
        return True

    def start_all_from_controller(self):
        clps = ClpController.listar() or []
        for clp in clps:
            try:
                self.start_poll_for(clp)
            except Exception:
                LOG.exception("Erro iniciando poller para %s", clp.get("ip"))

    def stop_all(self):
        ips = list(self._pollers.keys())
        for ip in ips:
            self.stop_poll_for(ip)

    def get_cache(self) -> Dict[str, Dict[str, Any]]:
        with self._global_lock:
            return copy.deepcopy(self._cache)

    def is_running(self, ip: str) -> bool:
        return ip in self._pollers


# Singleton (compatível com seu uso atual)
polling_service = PollingService()
