from flask import jsonify
from src.services.plc_service import CLPService
from src.utils.async_runner import async_loop

plc_service = CLPService()

def start_polling_controller(plc_id):
    plc = plc_service.buscar_clp_por_ip(plc_id)
    if not plc:
        return jsonify({'success': False, 'message': 'PLC não encontrado'}), 404

    future = async_loop.run_coro(plc_service.start_polling(plc_id))
    return jsonify({'success': True, 'message': 'Polling agendado'}), 202

def stop_polling_controller(plc_id):
    plc = plc_service.buscar_clp_por_ip(plc_id)
    if not plc:
        return jsonify({'success': False, 'message': 'PLC não encontrado'}), 404

    future = async_loop.run_coro(plc_service.stop_polling(plc_id))
    return jsonify({'success': True, 'message': 'Parada do polling agendada'}), 202
