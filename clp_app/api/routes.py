# clp_app/api/routes.py

from flask import Blueprint, jsonify, request, redirect, url_for
import logging
from threading import Thread

# Imports de utilidades
from utils import CLP as clp_manager, clp_functions
from utils import tags_manager  # NOVO: Importa o gerenciador de tags globais
# from clp_app.scanner.service import scanner_service
# from utils.log import caminho_coleta, caminho_app

def _run_in_thread(target, *args, **kwargs):
    t = Thread(target=target, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t

clp_bp = Blueprint("utils", __name__, url_prefix="/clp")


# --- ROTAS DE TAGS ATUALIZADAS ---

@clp_bp.route("/tags", methods=['POST'])
def add_global_tag():
    """Adiciona uma tag à lista global de tags."""
    data = request.get_json()
    new_tag = data.get('tag', '').strip()

    if not new_tag:
        return jsonify({"success": False, "message": "A tag não pode estar vazia"}), 400

    adicionada = tags_manager.adicionar_tag_global(new_tag)
    
    if adicionada:
        return jsonify({
            "success": True, 
            "message": "Tag adicionada com sucesso à lista global", 
            "tags": tags_manager.tags_globais
        })
    else:
        return jsonify({
            "success": True, # Sucesso mesmo que já exista, pois o estado final é o desejado
            "message": "Esta tag já existe na lista global", 
            "tags": tags_manager.tags_globais
        })

@clp_bp.route("/tags", methods=['GET'])
def get_all_tags():
    """Retorna a lista completa de tags globais salvas."""
    return jsonify({
        "success": True, 
        "tags": tags_manager.tags_globais
    })

@clp_bp.route("/<ip>/tags/assign", methods=['POST'])
def assign_tag_to_clp(ip):
    """Associa uma tag existente a um CLP específico."""
    clp_dict = clp_manager.buscar_por_ip(ip)
    if not clp_dict:
        return jsonify({"success": False, "message": "CLP não encontrado"}), 404

    data = request.get_json()
    tag_to_assign = data.get('tag', '').strip()

    if not tag_to_assign:
        return jsonify({"success": False, "message": "A tag para associar não pode estar vazia"}), 400

    # Garante que a lista de tags do CLP existe
    if 'tags' not in clp_dict:
        clp_dict['tags'] = []

    # Adiciona a tag ao CLP específico se ela ainda não existir
    if tag_to_assign not in clp_dict['tags']:
        clp_dict['tags'].append(tag_to_assign)
        clp_manager.salvar_clps() # Salva o arquivo clps.json com a tag associada
        return jsonify({"success": True, "message": "Tag associada com sucesso", "tags": clp_dict['tags']})
    else:
        return jsonify({"success": False, "message": "CLP já possui esta tag", "tags": clp_dict['tags']})
    

@clp_bp.route('/<ip>/tags/<tag>', methods=['DELETE'])
def unassign_tag_from_clp(ip, tag):
    """Desassocia uma tag de um CLP específico."""
    clp_dict = clp_manager.buscar_por_ip(ip)
    if not clp_dict:
        return jsonify({"success": False, "message": "CLP não encontrado"}), 404

    # Verifica se a lista de tags existe no CLP
    if 'tags' not in clp_dict or not isinstance(clp_dict['tags'], list):
        return jsonify({"success": False, "message": "Este CLP não possui tags para remover"}), 400

    # Tenta remover a tag da lista
    if tag in clp_dict['tags']:
        clp_dict['tags'].remove(tag)
        clp_manager.salvar_clps()  # Salva a alteração no clps.json
        return jsonify({
            "success": True, 
            "message": f"Tag '{tag}' removida com sucesso deste CLP",
            "tags": clp_dict['tags']  # Retorna a lista de tags atualizada
        })
    else:
        return jsonify({"success": False, "message": f"Tag '{tag}' não encontrada neste CLP"}), 404


# --- ROTAS ORIGINAIS DO CLP (mantidas como estavam) ---

@clp_bp.route("/<ip>/connect", methods=["POST"])
def clp_connect(ip):
    clp_dict = clp_manager.buscar_por_ip(ip)
    if not clp_dict:
        return jsonify({"ok": False, "error": "CLP não encontrado"}), 404

    data = request.json or {}
    porta_selecionada = data.get("port")

    def job():
        clp_functions.adicionar_log(clp_dict, f"Iniciando tentativa de conexão na porta {porta_selecionada}...")
        try:
            clp_functions.conectar(clp_dict, port=porta_selecionada)
            clp_functions.adicionar_log(clp_dict, f"Estado após tentar conectar: {clp_dict.get('conectado')}")
            clp_manager.salvar_clps()
        except Exception as e:
            clp_functions.adicionar_log(clp_dict, f"Erro durante conectar: {e}")
            clp_manager.salvar_clps()

    _run_in_thread(job)
    return jsonify({"ok": True, "messageCLP": "Conexão iniciada em background"})

@clp_bp.route("/<ip>/disconnect", methods=["POST"])
def clp_disconnect(ip):
    clp_dict = clp_manager.buscar_por_ip(ip)
    if not clp_dict:
        return jsonify({"ok": False, "error": "CLP não encontrado"}), 404
    try:
        clp_functions.desconectar(clp_dict)
        clp_manager.salvar_clps()
        status_info = clp_functions.get_info(clp_dict)["status"]
        return jsonify({"ok": True, "message": "Desconectado", "status": status_info})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@clp_bp.route("/<ip>/info", methods=["GET"])
def clp_info(ip):
    clp_dict = clp_manager.buscar_por_ip(ip)
    if not clp_dict:
        return jsonify({"ok": False, "error": "CLP não encontrado"}), 404
    return jsonify({"ok": True, "clp": clp_functions.get_info(clp_dict)})


@clp_bp.route("/<ip>/add_port", methods=["POST"])
def clp_add_port(ip):
    clp_dict = clp_manager.buscar_por_ip(ip)
    if not clp_dict:
        return jsonify({"ok": False, "error": "CLP não encontrado"}), 404

    data = request.json or {}
    porta = data.get("porta")
    if porta is None:
        return jsonify({"ok": False, "error": "porta obrigatória"}), 400

    try:
        clp_functions.adicionar_porta(clp_dict, int(porta))
        clp_manager.salvar_clps()
        return jsonify({"ok": True, "message": "Porta adicionada", "portas": clp_dict["PORTAS"]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@clp_bp.route("/<ip>/read_register", methods=["POST"])
def clp_read_register(ip):
    clp_dict = clp_manager.buscar_por_ip(ip)
    # Obtém o cliente de conexão a partir do módulo de funções
    client = clp_functions.get_client(ip)

    if not clp_dict or not client or not client.is_socket_open():
        return jsonify({"ok": False, "error": "CLP não conectado"}), 400

    data = request.json
    address = data.get("address")
    if address is None:
        return jsonify({"ok": False, "error": "Endereço é obrigatório"}), 400

    try:
        address = int(address)
        # unit=1 é o ID do escravo Modbus, padrão para muitas aplicações
        result = client.read_holding_registers(address, 1, unit=1)

        if result.isError():
            return jsonify({"ok": False, "error": "Erro Modbus ao ler registrador"})

        value = result.registers[0]
        return jsonify({"ok": True, "address": address, "value": value})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
        

# @clp_bp.route("/limpar_coleta_ip", methods=['POST'])
# def limpar_coleta_ip():
#     with open(caminho_coleta, "w", encoding="UTF-8"):
#         pass

    
#     return redirect(url_for("coleta_de_ips"))


# @clp_bp.route("/limpar_logs", methods=['POST'])
# def limpar_logs():
#     with open(caminho_app, "w", encoding="UTF-8"):
#         pass

    
    return redirect(url_for("logs_geral"))


@clp_bp.route('/rename', methods=['POST'])
def rename_clp():
    """Endpoint da API para renomear um CLP."""
    data = request.get_json()
    if not data or not data.get('ip') or not data.get('novo_nome'):
        return jsonify({'success': False, 'message': 'IP e novo nome são obrigatórios.'}), 400

    ip = data['ip']
    novo_nome = data['novo_nome'].strip()

    try:
        clp_alvo = clp_manager.buscar_por_ip(ip)
        if clp_alvo:
            clp_alvo['nome'] = novo_nome
            clp_manager.salvar_clps()
            return jsonify({'success': True, 'message': 'Nome atualizado com sucesso!'})
        else:
            return jsonify({'success': False, 'message': 'CLP não encontrado.'}), 404
    except Exception as e:
        logging.exception("Erro ao renomear CLP")
        return jsonify({'success': False, 'message': 'Erro interno no servidor.'}), 500


# --- Rotas do Scanner (não precisam de grandes mudanças) ---
# @clp_bp.route('/scanner/status', methods=['GET'])
# def get_scanner_status():
#     return jsonify({'status': scanner_service.get_status()})

# @clp_bp.route('/scanner/start', methods=['POST'])
# def start_scanner():
#     success = scanner_service.start()
#     return jsonify({'ok': success, 'status': scanner_service.get_status()})

# @clp_bp.route('/scanner/stop', methods=['POST'])
# def stop_scanner():
#     success = scanner_service.stop()
#     return jsonify({'ok': success, 'status': scanner_service.get_status()})

# NOTA: A rota 'baixar_codigo' foi removida pois dependia da subclasse CLPGen,
# que foi eliminada na refatoração. Ela pode ser recriada como uma função em
# 'clp_functions.py' se a funcionalidade for necessária.