# src/views/routes/coleta_routes.py  (ou módulo equivalente do blueprint `coleta`)
import threading
import json
import os
import logging
from datetime import datetime
from typing import Optional, List
from flask import Blueprint, current_app, jsonify, Response, render_template
from flask_login import login_required
from src.utils.decorators.decorators import role_required  

from src.utils.network.discovery import discovery_background_once, logger as discovery_logger
from src.utils.root.paths import DISCOVERY_FILE

# Blueprint da área de administração
coleta = Blueprint("coleta", __name__, url_prefix="/coleta")


# ---- Estado / sincronização ----
_disc_lock = threading.Lock()
_disc_thread: Optional[threading.Thread] = None
_disc_info = {
    "started_at": None,
    "last_finished_at": None,
}
# buffer de logs em memória
_disc_logs: List[str] = []
_logs_lock = threading.Lock()
_mem_log_handler: Optional[logging.Handler] = None


def _is_thread_running() -> bool:
    global _disc_thread
    return _disc_thread is not None and _disc_thread.is_alive()


def _clear_logs() -> None:
    with _logs_lock:
        _disc_logs.clear()


class MemoryLogHandler(logging.Handler):
    """Handler simples que guarda logs formatados em _disc_logs."""
    def __init__(self):
        super().__init__()
        self.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        with _logs_lock:
            _disc_logs.append(msg)
            # limite para evitar consumir muita memória
            if len(_disc_logs) > 5000:
                _disc_logs[:] = _disc_logs[-2000:]


def _attach_log_handler() -> logging.Handler:
    """Cria e anexa um handler ao logger do discovery. Retorna o handler."""
    global _mem_log_handler
    if _mem_log_handler:
        return _mem_log_handler
    handler = MemoryLogHandler()
    discovery_logger.addHandler(handler)
    _mem_log_handler = handler
    return handler


def _detach_log_handler() -> None:
    """Remove o handler se estiver anexado."""
    global _mem_log_handler
    if _mem_log_handler:
        try:
            discovery_logger.removeHandler(_mem_log_handler)
        except Exception:
            current_app.logger.exception("Erro ao remover MemoryLogHandler")
        _mem_log_handler = None


def _start_discovery_thread() -> bool:
    """Inicia a thread que executa discovery_background_once()."""
    global _disc_thread, _disc_info

    with _disc_lock:
        if _is_thread_running():
            return False

        # limpar buffer de logs ao iniciar nova execução
        _clear_logs()
        _attach_log_handler()

        def _worker():
            global _disc_thread
            try:
                _disc_info["started_at"] = datetime.utcnow().isoformat()
                # chama sua função pronta
                discovery_background_once()
                _disc_info["last_finished_at"] = datetime.utcnow().isoformat()
            except Exception as e:
                _disc_info["last_finished_at"] = datetime.utcnow().isoformat()
                current_app.logger.exception("Erro no worker de discovery: %s", e)
            finally:
                # garantir que o handler seja removido (evita duplicação em próximos starts)
                _detach_log_handler()
                # não manter referência à thread para permitir novo start
                with _disc_lock:
                    _disc_thread = None

        _disc_thread = threading.Thread(target=_worker, daemon=True)
        _disc_thread.start()
        return True


# ---- Rotas ----

@coleta.route("/", methods=["GET"])
@login_required
@role_required("admin")
def index():
    return render_template("coleta_ips.html")


@coleta.route("/start", methods=["POST"])
@login_required
@role_required("admin")
def coleta_ips_start():
    started = _start_discovery_thread()
    if not started:
        return ("discovery already running", 409)
    return ("started", 200)


@coleta.route("/status", methods=["GET"])
@login_required
@role_required("admin")
def coleta_ips_status():
    running = _is_thread_running()
    resp = {"running": running, "started_at": _disc_info.get("started_at"), "last_finished_at": _disc_info.get("last_finished_at")}
    try:
        if os.path.exists(DISCOVERY_FILE):
            stat = os.stat(DISCOVERY_FILE)
            resp["discovery_file_mtime"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            with open(DISCOVERY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            resp["result_count"] = len(data) if isinstance(data, list) else None
        else:
            resp["discovery_file_mtime"] = None
            resp["result_count"] = 0
    except Exception as e:
        current_app.logger.exception("Erro ao ler DISCOVERY_FILE: %s", e)
        resp["discovery_file_mtime"] = None
        resp["result_count"] = None
    return jsonify(resp)


@coleta.route("/logs", methods=["GET"])
@login_required
@role_required("admin")
def coleta_ips_logs():
    """Retorna logs em tempo real (texto)."""
    with _logs_lock:
        text = "\n".join(_disc_logs)
    return Response(text, mimetype="text/plain")


@coleta.route("/results", methods=["GET"])
@login_required
@role_required("admin")
def coleta_ips_results():
    try:
        if not os.path.exists(DISCOVERY_FILE):
            return ("no discovery file", 404)
        with open(DISCOVERY_FILE, "r", encoding="utf-8") as f:
            text = f.read()
        return Response(text, mimetype="application/json")
    except Exception as e:
        current_app.logger.exception("Erro ao abrir DISCOVERY_FILE: %s", e)
        return ("error reading discovery file", 500)