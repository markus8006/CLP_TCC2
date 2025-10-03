# run.py
import threading
import time
from src.app import create_app
from src.services.polling_service import polling_service
from src.utils.log.log import setup_logger
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusDeviceContext, ModbusServerContext, ModbusSequentialDataBlock
from pymodbus.pdu.device import ModbusDeviceIdentification

logger = setup_logger()

def start_modbus_simulator(host="127.0.0.1", port=5020):
    store1 = ModbusDeviceContext(hr=ModbusSequentialDataBlock(0, [0]*10))
    store2 = ModbusDeviceContext(hr=ModbusSequentialDataBlock(0, [100 + i for i in range(5)]))
    context = ModbusServerContext(devices={1: store1, 2: store2}, single=False)
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'Simulated CLP'
    identity.ProductCode = 'SIM'
    identity.ProductName = 'SimCLP'
    identity.MajorMinorRevision = '1.0'
    logger.info("Iniciando servidor Modbus TCP em %s:%s", host, port)
    StartTcpServer(context=context, identity=identity, address=(host, port))

def main():
    app = create_app()

    # 1) anexa a app ao polling_service (permitirá persistência dentro das threads)
    polling_service.set_app(app)

    # 2) Inicia simulador em thread (opcional)
    # t = threading.Thread(target=start_modbus_simulator, kwargs={"host": "127.0.0.1", "port": 5020}, daemon=True)
    # t.start()
    # time.sleep(1)

    # 3) Chame start_all_from_controller() DENTRO do app context
    with app.app_context():
        try:
            polling_service.start_all_from_controller()
            logger.info("PollingService: pollers iniciados a partir do banco")
        except Exception as e:
            logger.exception("Erro ao iniciar pollers: %s", e)


    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

if __name__ == "__main__":
    main()
