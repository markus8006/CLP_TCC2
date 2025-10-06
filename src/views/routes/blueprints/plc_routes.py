from flask import Blueprint, request
from src.controllers.plc_controller import start_polling_controller, stop_polling_controller

plc_bp = Blueprint('plc', __name__)

@plc_bp.route('/plcs/<int:plc_id>/start', methods=['POST'])
def start_plc(plc_id):
    return start_polling_controller(plc_id)

@plc_bp.route('/plcs/<int:plc_id>/stop', methods=['POST'])
def stop_plc(plc_id):
    return stop_polling_controller(plc_id)
