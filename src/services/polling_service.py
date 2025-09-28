# src/services/polling_service.py
import threading
import time
import yaml
import copy
from typing import Dict, Any, List, Optional, Tuple

from src.adapters.modbus_adapter import ModbusAdapter
from src.controllers.clp_controller import ClpController
from src.utils.log.log import setup_logger

LOG = setup_logger()

MODBUS_MAX_REGS = 125  # limite por request (função 3/4)

# ---------------------------------------------------
# util: montar batches simples de leituras contíguas
# entrada: lista de dicts {name,type,address,count,interval?}
# saída: list[(type, start_addr, count, [reg_dicts])]
# ---------------------------------------------------
def build_batches(registers: List[Dict[str, Any]]) -> List[Tuple[str, int, int, List[Dict[str, Any]]]]:
    # agrupa por tipo (holding,input,coils,discrete)
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
                # cabe no grupo se é contíguo ou overlap (<= end+1) e não ultrapassa limite total
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
# Poller de um CLP (thread)
# ---------------------------------------------------
class CLPPoller(threading.Thread):
    def __init__(self, clp: Dict[str, Any], adapter: ModbusAdapter, cache: Dict[str, Any], stop_event: threading.Event):
        super().__init__(daemon=True, name=f"CLPPoller-{clp.get('ip')}")
        self.clp = clp
        self.adapter = adapter
        self.cache = cache
        self.stop_event = stop_event
        self._last_read: Dict[str, float] = {}
        self._lock = threading.RLock()

    def _load_registers_config(self) -> List[Dict[str, Any]]:
        """
        Prefer clp['registers'] (editável na UI). Se não existir, tenta carregar um arquivo YAML fallback.
        Formato esperado por register:
          {
            "name": "temp1",
            "type": "holding",
            "address": 100,
            "count": 2,
            "interval": 2
          }
        """
        regs = self.clp.get("registers")
        if regs and isinstance(regs, list):
            return regs

        # fallback para arquivo yaml (opcional)
        try:
            with open("src/config/plc_registers.yaml", "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            devices = cfg.get("devices", [])
            for d in devices:
                if d.get("host") == self.clp.get("ip") or d.get("name") == self.clp.get("nome"):
                    return d.get("registers", [])
        except FileNotFoundError:
            LOG.debug("plc_registers.yaml não encontrado; nenhum registro configurado para %s", self.clp.get("ip"))
        except Exception as e:
            LOG.exception("Erro lendo plc_registers.yaml: %s", e)
        return []

    def _should_read(self, reg: Dict[str, Any], now: float) -> bool:
        interval = int(reg.get("interval") or self.clp.get("default_interval") or 5)
        last = self._last_read.get(reg["name"], 0)
        return (now - last) >= interval

    def _update_clp_and_cache(self, reg_name: str, value: Any):
        ts = time.time()
        # cache local
        with self._lock:
            self.cache.setdefault(self.clp.get("ip"), {})
            self.cache[self.clp.get("ip")][reg_name] = {"value": value, "timestamp": ts}
        # persistir no clp via ClpController (usa editar_clp(old, new) conforme seu padrão)
        try:
            clp_current = ClpController.obter_por_ip(self.clp.get("ip"))
            if not clp_current:
                LOG.warning("CLPPoller: CLP não encontrado ao atualizar cache %s", self.clp.get("ip"))
                return
            # manter chave registers_values para exposição / UI
            clp_current.setdefault("registers_values", {})
            clp_current["registers_values"][reg_name] = {"value": value, "timestamp": ts}
            # chamar editar_clp passando old e new (conforme seu uso atual)
            ClpController.editar_clp(ClpController.obter_por_ip(self.clp.get("ip")), clp_current)
        except Exception as e:
            LOG.exception("Erro atualizando ClpController para %s: %s", self.clp.get("ip"), e)

    def run(self):
        ip = self.clp.get("ip")
        LOG.info("CLPPoller[%s] iniciado", ip)
        adapter = self.adapter
        # tentamos conectar antes do loop; adapter.connect atualiza logs do clp
        try:
            adapter.connect(self.clp)
        except Exception:
            LOG.debug("Falha inicial de connect para %s", ip)

        while not self.stop_event.is_set():
            now = time.time()
            registers = self._load_registers_config()
            if not registers:
                # sem registradores configurados - dorme e tenta depois
                time.sleep(2.0)
                continue

            batches = build_batches(registers)
            for rtype, start, count, group in batches:
                # checar se algum reg do grupo precisa leitura agora
                needs = False
                for reg in group:
                    if self._should_read(reg, now):
                        needs = True
                        break
                if not needs:
                    continue

                # garantir conexão (adapter gerencia conexões internas)
                if not adapter.connect(self.clp):
                    LOG.warning("CLPPoller[%s] não conectou; pulando batch %s:%s", ip, start, count)
                    continue

                # efetuar leitura (usamos adapter.read_tag que faz read_holding_registers)
                try:
                    raw = adapter.read_tag(self.clp, start, count)
                except Exception as e:
                    LOG.exception("CLPPoller read_tag exception %s %s", ip, e)
                    raw = None

                if not raw:
                    # falha na leitura
                    LOG.debug("CLPPoller[%s] read retornou vazio em %s:%s", ip, start, count)
                    continue

                # mapear respostas para cada register do group
                for reg in group:
                    name = reg["name"]
                    addr = int(reg["address"])
                    cnt = int(reg.get("count", 1))
                    offset = addr - start
                    segment = []
                    try:
                        # raw pode ser lista de inteiros (holding/input) ou booleans (coils/discrete)
                        segment = raw[offset: offset + cnt]
                    except Exception:
                        LOG.exception("Erro ao separar segmento para %s %s", ip, name)
                        segment = None

                    if segment is None or len(segment) == 0:
                        continue

                    # simples decode: se um único reg -> inteiro/boolean; se múltiplos -> lista
                    value = segment[0] if len(segment) == 1 else segment
                    # opcional: aplicar decoders se houver reg['decoder'] (int32,float32, etc) - deixar simples aqui

                    # atualizar cache + controller
                    self._update_clp_and_cache(name, value)
                    self._last_read[name] = now

                # pausa curta entre batches para não saturar
                if self.stop_event.is_set():
                    break
                time.sleep(0.05)

            # loop sleep: 0.5s granularity — intervalos por registro decidem leitura real
            time.sleep(0.5)

        # on stop: desconectar
        try:
            adapter.disconnect(self.clp)
        except Exception:
            pass
        LOG.info("CLPPoller[%s] finalizado", ip)


# ---------------------------------------------------
# Serviço que gerencia pollers
# ---------------------------------------------------
class PollingService:
    def __init__(self, adapter: Optional[ModbusAdapter] = None):
        self.adapter = adapter or ModbusAdapter()
        self._pollers: Dict[str, CLPPoller] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._global_lock = threading.RLock()

    def start_poll_for(self, clp: Dict[str, Any]) -> bool:
        ip = clp.get("ip")
        if not ip:
            return False
        with self._global_lock:
            if ip in self._pollers:
                LOG.info("PollingService: poller já ativo para %s", ip)
                return True
            stop_event = threading.Event()
            poller = CLPPoller(clp=clp, adapter=self.adapter, cache=self._cache, stop_event=stop_event)
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
            # cleanup
            self._pollers.pop(ip, None)
            self._stop_events.pop(ip, None)
            LOG.info("PollingService: parado poller para %s", ip)
        return True

    def start_all_from_controller(self):
        """
        Inicia pollers para todos CLPs retornados pelo ClpController.listar()
        Ideal rodar no startup da aplicação (se apropriado).
        """
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
        # devolve cópia para evitar race conditions
        with self._global_lock:
            return copy.deepcopy(self._cache)

    def is_running(self, ip: str) -> bool:
        return ip in self._pollers

# Instância singleton para ser importada onde precisar
polling_service = PollingService()
