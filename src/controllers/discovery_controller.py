# src/controllers/discovery_controller.py
from flask import jsonify, request, current_app
from flask_login import login_required
from src.services.discovery_service import AutoDiscoveryService
from src.utils.decorators.decorators import role_required
import logging

logger = logging.getLogger(__name__)

def start_auto_discovery():
    """
    Endpoint para iniciar descoberta automática de CLPs
    POST /api/discovery/auto
    """
    try:
        data = request.get_json() or {}
        
        # Parâmetros opcionais
        target_interfaces = data.get('interfaces')  # Lista de interfaces específicas
        auto_activate = data.get('auto_activate', True)  # Ativar automaticamente
        overwrite_existing = data.get('overwrite_existing', False)  # Sobrescrever existentes
        
        logger.info(f"Iniciando descoberta automática - Interfaces: {target_interfaces}")
        
        # Executar descoberta
        service = AutoDiscoveryService()
        results = service.discover_and_save_plcs(
            target_interfaces=target_interfaces,
            auto_activate=auto_activate,
            overwrite_existing=overwrite_existing
        )
        
        return jsonify({
            'success': True,
            'message': 'Descoberta automática concluída',
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Erro na descoberta automática: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro na descoberta: {str(e)}'
        }), 500

def get_discovered_plcs():
    """
    Endpoint para obter PLCs descobertos automaticamente
    GET /api/discovery/plcs
    """
    try:
        service = AutoDiscoveryService()
        plcs = service.get_discovered_plcs_summary()
        
        return jsonify({
            'success': True,
            'plcs': plcs,
            'count': len(plcs)
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao obter PLCs descobertos: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def rediscover_plcs():
    """
    Endpoint para redescobrir PLCs específicos
    POST /api/discovery/rediscover
    """
    try:
        data = request.get_json() or {}
        plc_ids = data.get('plc_ids')  # Lista de IDs ou None para todos
        
        service = AutoDiscoveryService()
        results = service.rediscover_plcs(plc_ids=plc_ids)
        
        return jsonify(results), 200 if results.get('success') else 500
        
    except Exception as e:
        logger.error(f"Erro na redescoberta: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Rotas para blueprint
def setup_discovery_routes(bp):
    """Configura as rotas de descoberta no blueprint"""
    
    @bp.route('/discovery/auto', methods=['POST'])
    @login_required
    @role_required('admin')
    def auto_discover():
        return start_auto_discovery()
    
    @bp.route('/discovery/plcs', methods=['GET'])
    @login_required
    @role_required(['admin', 'supervisor'])
    def get_plcs():
        return get_discovered_plcs()
    
    @bp.route('/discovery/rediscover', methods=['POST'])
    @login_required
    @role_required('admin')
    def rediscover():
        return rediscover_plcs()