# src/views/routes/coleta_routes.py
import threading
import json
import os
import logging
import ipaddress
from datetime import datetime
from typing import Optional, List, Dict

from flask import (
    Blueprint, current_app, jsonify, Response, render_template, 
    request, redirect, url_for, flash
)
from flask_login import login_required

from src.utils.decorators.decorators import role_required
from src.utils.network.discovery import discovery_background_once, logger as discovery_logger
from src.utils.root.paths import DISCOVERY_FILE
from src.services.clp_service import CLPService # Refatorado para usar o novo serviço

# Blueprint
coleta = Blueprint("coleta", __name__, url_prefix="/coleta")

# ---- Gerenciamento da Thread de Descoberta (Lógica de Controle da Rota) ----
# (Esta seção lida com o estado da thread e os logs da descoberta, 
#  o que é uma responsabilidade apropriada para a camada de rotas/views,
#  pois controla uma tarefa de background iniciada pelo usuário.
#  Nenhuma alteração necessária aqui.)

_disc_lock = threading.Lock()
_disc_thread: Optional[threading.Thread] = None
_disc_info = {"started_at": None, "last_finished_at": None}
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
    global _mem_log_handler
    if _mem_log_handler:
        return _mem_log_handler
    handler = MemoryLogHandler()
    discovery_logger.addHandler(handler)
    _mem_log_handler = handler
    return handler

def _detach_log_handler() -> None:
    global _mem_log_handler
    if _mem_log_handler:
        try:
            discovery_logger.removeHandler(_mem_log_handler)
        except Exception:
            current_app.logger.exception("Erro ao remover MemoryLogHandler")
        _mem_log_handler = None

def _start_discovery_thread() -> bool:
    global _disc_thread, _disc_info
    with _disc_lock:
        if _is_thread_running():
            return False
        
        _clear_logs()
        _attach_log_handler()

        def _worker():
            global _disc_thread
            try:
                # O ideal é que discovery_background_once() também use o CLPService
                # para salvar os resultados, mas por agora mantemos o foco na rota.
                discovery_background_once() 
            finally:
                _detach_log_handler()
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
    except (IOError, json.JSONDecodeError):
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
        return Response(open(DISCOVERY_FILE, "r", encoding="utf-8").read(), mimetype="application/json")
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

        portas_list = [
            int(p.strip()) for p in request.form.get("portas", "").split(",") if p.strip().isdigit()
        ]

        # Monta o dicionário de dados
        dados_clp = {
            "ip": ip,
            "nome": nome,
            "mac": request.form.get("mac", "").strip(),
            "subnet": request.form.get("subnet", "").strip(),
            "portas": ",".join(map(str, portas_list)), # O modelo espera uma string
            "tipo": "CLP",
            "ativo": True,
            "manual": True,
        }

        try:
            # Delega a criação ou atualização para o serviço
            CLPService.criar_ou_atualizar_clp(dados_clp)
            flash(f"CLP {ip} foi salvo com sucesso!", "success")
        except Exception as e:
            flash(f"Ocorreu um erro ao salvar o CLP: {e}", "danger")

        return redirect(url_for("coleta.coleta_manual"))

    # Para o método GET, buscamos os CLPs através do serviço
    clps_salvos = CLPService.buscar_todos_clps()
    return render_template("clps/clp_manual.html", clps=clps_salvos)