from src.views import create_app
from src.services.polling_service import polling_service
import threading
from src.utils.log.log import setup_logger
from pymodbus.server import StartTcpServer
from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusServerContext,
    ModbusSequentialDataBlock
)
from pymodbus.pdu.device import ModbusDeviceIdentification

# --- Logger ---
logger = setup_logger()

# --- Flask App ---
# I cannot correct this part as the "src" directory was not provided.
# I am assuming it is correct.
app = create_app()


# --- Simulação Modbus ---
def simulation():
    """
    This function creates and runs a Modbus TCP server with two simulated devices.
    """
    # --- Create simulated devices' data stores ---
    # Device 1 with 10 holding registers starting at address 0, initialized to 0.
    store1 = ModbusDeviceContext(
        hr=ModbusSequentialDataBlock(0, [0]*10),
        di=ModbusSequentialDataBlock(0, [0]*10),
        co=ModbusSequentialDataBlock(0, [0]*10),
        ir=ModbusSequentialDataBlock(0, [0]*10)
    )

    # Device 2 with 5 holding registers starting at address 0, initialized to 100.
    store2 = ModbusDeviceContext(
        hr=ModbusSequentialDataBlock(0, [100]*5),
        di=ModbusSequentialDataBlock(0, [0]*5),
        co=ModbusSequentialDataBlock(0, [0]*5),
        ir=ModbusSequentialDataBlock(0, [0]*5)
    )

    # --- Create server context with multiple devices ---
    # The `devices` argument is a dictionary mapping the device ID to its datastore.
    # `single=False` indicates that we are providing more than one device.
    context = ModbusServerContext(devices={1: store1, 2: store2}, single=False)

    # --- Identificação do servidor ---
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'Simulated CLP'
    identity.ProductCode = 'SIM'
    identity.VendorUrl = 'http://localhost'
    identity.ProductName = 'SimCLP'
    identity.ModelName = 'SimCLP v1'
    identity.MajorMinorRevision = '1.0'

    # --- Rodar servidor TCP ---
    logger.info("Servidor Modbus TCP rodando em 127.0.0.1:5020")
    StartTcpServer(context=context, identity=identity, address=("127.0.0.1", 5020))


# --- Main ---
if __name__ == "__main__":
    # Iniciar polling service
    # I cannot correct this part as the "src" directory was not provided.
    # I am assuming it is correct.
    polling_service.start_all_from_controller()

    # Rodar servidor Modbus em thread separada
    threading.Thread(target=simulation, daemon=True).start()

    # Rodar Flask
    logger.info("Servidor Flask rodando em 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)