from src.views import create_app
from src.services.polling_service import polling_service
import threading
import time  # <-- 1. Importe a biblioteca time
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
app = create_app()


# --- Simulação Modbus ---
def simulation():
    # ... (seu código de simulação permanece o mesmo)
    store1 = ModbusDeviceContext(hr=ModbusSequentialDataBlock(0, [0]*10))
    store2 = ModbusDeviceContext(hr=ModbusSequentialDataBlock(0, [100]*5))
    context = ModbusServerContext(devices={1: store1, 2: store2}, single=False)
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'Simulated CLP'
    # ... (resto da identificação)
    logger.info("Servidor Modbus TCP rodando em 127.0.0.1:5020")
    StartTcpServer(context=context, identity=identity, address=("127.0.0.1", 5020))


# --- Main ---
if __name__ == "__main__":
    # Rodar servidor Modbus em thread separada PRIMEIRO
    threading.Thread(target=simulation, daemon=True).start()

    # <-- 2. Adicione uma pequena pausa aqui
    logger.info("Aguardando o servidor Modbus iniciar...")
    time.sleep(1)  # Espera 1 segundo para garantir que o servidor esteja no ar

    # Agora, inicie o polling service
    polling_service.start_all_from_controller()

    # Rodar Flask
    logger.info("Servidor Flask rodando em 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)