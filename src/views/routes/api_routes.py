# src/views/api_routes.py
from flask import Blueprint, jsonify, request
import logging
from threading import Thread

from src.controllers.clp_controller import ClpController
from src.controllers.tag_controller import TagController
from src.services.connection_service import (
    conectar as connection_conectar,
    desconectar as connection_desconectar,
    get_client as connection_get_client,
    adicionar_log as connection_adicionar_log
)
from src.services.device_service import salvar_clps

clp_api = Blueprint("clp_api", __name__, url_prefix="/clp")


def _run_in_thread(target, *args, **kwargs):
    t = Thread(target=target, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t


# -------------------------
# Rotas de Tags (globais)
# -------------------------
@clp_api.route("/tags", methods=['POST'])
def add_global_tag():
    """Adiciona uma tag à lista global de tags."""
    data = request.get_json() or {}
    new_tag = (data.get('tag') or "").strip()

    if not new_tag:
        return jsonify({"success": False, "message": "A tag não pode estar vazia"}), 400

    created = TagController.adicionar_tag(new_tag)
    # retorna a lista completa de nomes de tag (compatível com front antigo)
    tags = [t["nome"] for t in TagController.listar_tags()]
    if created:
        return jsonify({
            "success": True,
            "message": "Tag adicionada com sucesso à lista global",
            "tags": tags
        }), 201
    else:
        # já existia — consideramos "sucesso" porque o estado final é o desejado
        return jsonify({
            "success": True,
            "message": "Esta tag já existe na lista global",
            "tags": tags
        }), 200


@clp_api.route("/tags", methods=['GET'])
def get_all_tags():
    """Retorna a lista completa de tags globais salvas."""
    tags = [t["nome"] for t in TagController.listar_tags()]
    return jsonify({"success": True, "tags": tags})


# -------------------------
# Associa / desassocia tag em CLP
# -------------------------
@clp_api.route("/<ip>/tags/assign", methods=['POST'])
def assign_tag_to_clp(ip):
    """Associa uma tag existente a um CLP específico."""
    clp_dict = ClpController.obter_por_ip(ip)
    if not clp_dict:
        return jsonify({"success": False, "message": "CLP não encontrado"}), 404

    data = request.get_json() or {}
    tag_to_assign = (data.get('tag') or "").strip()
    if not tag_to_assign:
        return jsonify({"success": False, "message": "A tag para associar não pode estar vazia"}), 400

    # garante lista de tags no CLP
    tags = clp_dict.setdefault("tags", [])

    if tag_to_assign in tags:
        return jsonify({"success": False, "message": "CLP já possui esta tag", "tags": tags}), 409

    tags.append(tag_to_assign)

    # salva no JSON e garante que a tag exista também nas tags globais
    try:
        salvar_clps()
        TagController.adicionar_tag(tag_to_assign)  # idempotente
        return jsonify({"success": True, "message": "Tag associada com sucesso", "tags": tags}), 200
    except Exception as e:
        logging.exception("Erro ao associar tag ao CLP")
        return jsonify({"success": False, "message": "Erro interno ao salvar tag", "error": str(e)}), 500


@clp_api.route('/<ip>/tags/<tag>', methods=['DELETE'])
def unassign_tag_from_clp(ip, tag):
    """Desassocia uma tag de um CLP específico."""
    clp_dict = ClpController.obter_por_ip(ip)
    if not clp_dict:
        return jsonify({"success": False, "message": "CLP não encontrado"}), 404

    tags = clp_dict.get("tags", [])
    if not isinstance(tags, list) or not tags:
        return jsonify({"success": False, "message": "Este CLP não possui tags para remover"}), 400

    if tag in tags:
        tags.remove(tag)
        try:
            salvar_clps()
            return jsonify({
                "success": True,
                "message": f"Tag '{tag}' removida com sucesso deste CLP",
                "tags": tags
            }), 200
        except Exception as e:
            logging.exception("Erro ao remover tag do CLP")
            return jsonify({"success": False, "message": "Erro interno ao salvar alterações", "error": str(e)}), 500
    else:
        return jsonify({"success": False, "message": f"Tag '{tag}' não encontrada neste CLP"}), 404


# -------------------------
# Rotas de conexão / controle do CLP
# -------------------------
@clp_api.route("/<ip>/connect", methods=["POST"])
def clp_connect(ip):
    """Inicia a tentativa de conexão (em thread) para não travar o request."""
    clp_dict = ClpController.obter_por_ip(ip)
    if not clp_dict:
        return jsonify({"ok": False, "error": "CLP não encontrado"}), 404

    data = request.json or {}
    porta_selecionada = data.get("port")

    def job():
        try:
            connection_adicionar_log(clp_dict, f"Iniciando tentativa de conexão na porta {porta_selecionada}...")
            # usa o service de conexão diretamente para maior controle
            ok = connection_conectar(clp_dict, port=porta_selecionada)
            connection_adicionar_log(clp_dict, f"Estado após tentar conectar: {clp_dict.get('conectado')}")
            salvar_clps()
        except Exception as e:
            logging.exception("Erro durante tentativa de conexão em background")
            # garante log
            connection_adicionar_log(clp_dict, f"Erro durante conectar: {e}")
            try:
                salvar_clps()
            except Exception:
                logging.exception("Erro salvando after-failure")

    _run_in_thread(job)
    return jsonify({"ok": True, "message": "Conexão iniciada em background"}), 202


@clp_api.route("/<ip>/disconnect", methods=["POST"])
def clp_disconnect(ip):
    clp_dict = ClpController.obter_por_ip(ip)
    if not clp_dict:
        return jsonify({"ok": False, "error": "CLP não encontrado"}), 404
    try:
        connection_desconectar(clp_dict)
        salvar_clps()
        status_info = "Online" if clp_dict.get("conectado") else "Offline"
        return jsonify({"ok": True, "message": "Desconectado", "status": status_info}), 200
    except Exception as e:
        logging.exception("Erro ao desconectar CLP")
        return jsonify({"ok": False, "error": str(e)}), 500


@clp_api.route("/<ip>/info", methods=["GET"])
def clp_info(ip):
    """Retorna informações de status do CLP (compatível com antigo get_info)."""
    clp_dict = ClpController.obter_por_ip(ip)
    if not clp_dict:
        return jsonify({"ok": False, "error": "CLP não encontrado"}), 404

    # constrói objeto de informações (compatível com versão antiga)
    info = {
        "ip": clp_dict.get("ip"),
        "unidade": clp_dict.get("unidade"),
        "portas": clp_dict.get("portas") or clp_dict.get("PORTAS") or [],
        "conectado": bool(clp_dict.get("conectado")),
        "data_registro": clp_dict.get("data_registro"),
        "nome": clp_dict.get("nome"),
        "descricao": clp_dict.get("descricao"),
        "logs": clp_dict.get("logs", []),
        "status": "Online" if clp_dict.get("conectado") else "Offline",
        "tags": clp_dict.get("tags", [])
    }
    return jsonify({"ok": True, "clp": info}), 200


@clp_api.route("/<ip>/add_port", methods=["POST"])
def clp_add_port(ip):
    """Adiciona uma porta conhecida ao CLP (e salva)."""
    clp_dict = ClpController.obter_por_ip(ip)
    if not clp_dict:
        return jsonify({"ok": False, "error": "CLP não encontrado"}), 404

    data = request.json or {}
    porta = data.get("porta")
    if porta is None:
        return jsonify({"ok": False, "error": "porta obrigatória"}), 400

    try:
        portas = clp_dict.setdefault("portas", clp_dict.get("PORTAS", []))
        porta_int = int(porta)
        if porta_int not in portas:
            portas.append(porta_int)
            # mantem ordenado e sem duplicatas
            clp_dict["portas"] = sorted(list(set(portas)))
            salvar_clps()
        return jsonify({"ok": True, "message": "Porta adicionada", "portas": clp_dict.get("portas")}), 200
    except Exception as e:
        logging.exception("Erro ao adicionar porta")
        return jsonify({"ok": False, "error": str(e)}), 500


@clp_api.route("/<ip>/read_register", methods=["POST"])
def clp_read_register(ip):
    """Lê um registrador via Modbus a partir do cliente ativo."""
    clp_dict = ClpController.obter_por_ip(ip)
    client = connection_get_client(ip)

    if not clp_dict or not client or not getattr(client, "is_socket_open", lambda: False)():
        return jsonify({"ok": False, "error": "CLP não conectado"}), 400

    data = request.json or {}
    address = data.get("address")
    if address is None:
        return jsonify({"ok": False, "error": "Endereço é obrigatório"}), 400

    try:
        address = int(address)
        # unit=1 é o ID do escravo Modbus (ajuste se necessário)
        result = client.read_holding_registers(address, 1, unit=1)
        # pymodbus retorna objeto; checagem genérica de erro:
        if hasattr(result, "isError") and result.isError():
            return jsonify({"ok": False, "error": "Erro Modbus ao ler registrador"}), 500

        value = None
        # tenta extrair valor com segurança
        if hasattr(result, "registers") and result.registers:
            value = result.registers[0]
        else:
            # algumas versões retornam .bits ou .register
            value = getattr(result, "registers", None)

        return jsonify({"ok": True, "address": address, "value": value}), 200
    except Exception as e:
        logging.exception("Erro lendo registrador Modbus")
        return jsonify({"ok": False, "error": str(e)}), 500


# -------------------------
# Utilitário: renomear CLP
# -------------------------
@clp_api.route('/rename', methods=['POST'])
def rename_clp():
    """Endpoint da API para renomear um CLP."""
    data = request.get_json() or {}
    ip = data.get('ip')
    novo_nome = (data.get('novo_nome') or "").strip()
    if not ip or not novo_nome:
        return jsonify({'success': False, 'message': 'IP e novo nome são obrigatórios.'}), 400

    try:
        clp_alvo = ClpController.obter_por_ip(ip)
        if clp_alvo:
            clp_alvo['nome'] = novo_nome
            salvar_clps()
            return jsonify({'success': True, 'message': 'Nome atualizado com sucesso!'}), 200
        else:
            return jsonify({'success': False, 'message': 'CLP não encontrado.'}), 404
    except Exception as e:
        logging.exception("Erro ao renomear CLP")
        return jsonify({'success': False, 'message': 'Erro interno no servidor.'}), 500
    

@clp_api.route("/adicionar_tag/<ip>", methods=["POST"])
def adicionar_tags(ip):
    clp = ClpController.obter_por_ip(ip)
    clp_tags = clp[""]



