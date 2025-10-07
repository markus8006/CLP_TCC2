import threading
import json
import os
import logging
import ipaddress
from typing import Optional, List

from flask import (
    Blueprint, current_app, jsonify, Response, render_template,
    request, redirect, url_for, flash
)
from flask_login import login_required

from src.utils.decorators.decorators import role_required
from src.services.discovery_service import AutoDiscoveryService
from src.services.plc_service import CLPService
from src.utils.root.paths import DISCOVERY_FILE

coleta = Blueprint("coleta", __name__, url_prefix="/coleta")

logger = logging.getLogger(__name__)


service = CLPService()

_disc_lock = threading.Lock()
_disc_thread: Optional[threading.Thread] = None
_disc_info = {"started_at": None, "last_finished_at": None}
_disc_logs: List[str] = []
_logs_lock = threading.Lock()

def _is_thread_running() -> bool:
    global _disc_thread
    return _disc_thread is not None and _disc_thread.is_alive()

def _clear_logs() -> None:
    with _logs_lock:
        _disc_logs.clear()

class MemoryLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        with _logs_lock:
            _disc_logs.append(msg)
            if len(_disc_logs) > 5000:
                _disc_logs[:] = _disc_logs[-2000:]

def _attach_log_handler() -> logging.Handler:
    handler = MemoryLogHandler()
    logger.addHandler(handler)
    return handler

def _detach_log_handler(handler: logging.Handler) -> None:
    try:
        logger.removeHandler(handler)
    except Exception:
        current_app.logger.exception("Erro ao remover MemoryLogHandler")

def _start_discovery_thread() -> bool:
    global _disc_thread
    with _disc_lock:
        if _is_thread_running():
            return False

        _clear_logs()
        handler = _attach_log_handler()

        def _worker():
            nonlocal handler
            try:
                service = AutoDiscoveryService()
                service.discover_and_save_plcs()
            except Exception as e:
                logger.error(f"Erro na descoberta automática: {e}")
            finally:
                _detach_log_handler(handler)
                with _disc_lock:
                    global _disc_thread
                    _disc_thread = None

        _disc_thread = threading.Thread(target=_worker, daemon=True)
        _disc_thread.start()
        return True

@coleta.route("/", methods=["GET"])
@login_required
@role_required("admin")
def index():
    return render_template("coleta_ips.html")

@coleta.route("/start", methods=["POST"])
@login_required
@role_required("admin")
def coleta_ips_start():
    if _start_discovery_thread():
        return "Descoberta iniciada", 200
    return "Descoberta já em andamento", 409

@coleta.route("/status", methods=["GET"])
@login_required
@role_required("admin")
def coleta_ips_status():
    running = _is_thread_running()
    resp = {"running": running}
    try:
        if os.path.exists(DISCOVERY_FILE):
            with open(DISCOVERY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            resp["result_count"] = len(data)
        else:
            resp["result_count"] = 0
    except Exception:
        resp["result_count"] = 0
    return jsonify(resp)

@coleta.route("/logs", methods=["GET"])
@login_required
@role_required("admin")
def coleta_ips_logs():
    with _logs_lock:
        return Response("\n".join(_disc_logs), mimetype="text/plain")

@coleta.route("/results", methods=["GET"])
@login_required
@role_required("admin")
def coleta_ips_results():
    try:
        with open(DISCOVERY_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        return Response(content, mimetype="application/json")
    except FileNotFoundError:
        return jsonify([])
    except Exception as e:
        current_app.logger.error(f"Erro ao ler arquivo de resultados: {e}")
        return "Erro ao ler resultados", 500


@coleta.route("/manual", methods=["GET", "POST"])
@login_required
@role_required("admin")
def coleta_manual():
    if request.method == "POST":
        ip = request.form.get("ip", "").strip()
        nome = request.form.get("nome", "").strip()

        if not ip or not nome:
            flash("IP e Nome são obrigatórios.", "danger")
            return redirect(url_for("coleta.coleta_manual"))
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            flash("Endereço IP inválido.", "danger")
            return redirect(url_for("coleta.coleta_manual"))

        portas_str = request.form.get("portas", "")
        portas_list = [
            int(p.strip()) for p in portas_str.split(",") if p.strip().isdigit()
        ]

        dados_clp = {
            "ip_address": ip,
            "name": nome,
            "mac": request.form.get("mac", "").strip(),
            "subnet": request.form.get("subnet", "").strip(),
            "portas": portas_list,
            "tipo": "CLP",
            "is_active": True,
            "manual": True,
        }

        try:
            service.criar_ou_atualizar_clp(dados_clp)
            flash(f"CLP {ip} foi salvo com sucesso!", "success")
        except Exception as e:
            current_app.logger.error(f"ERRO AO SALVAR CLP MANUAL: {e}")
            flash(f"Ocorreu um erro ao salvar o CLP: {e}", "danger")

        return redirect(url_for("coleta.coleta_manual"))

    # GET - busca CLPs para listar
    clps_salvos = service.buscar_todos_clps()
    return render_template("clps/clp_manual.html", clps=clps_salvos)
