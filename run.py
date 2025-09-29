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
import asyncio
from pymodbus.server import StartAsyncTcpServer




# --- Simulação Modbus ---

def simulation():
    """
    Cria e executa um servidor Modbus TCP síncrono e estável com um único dispositivo.
    Esta é a forma mais robusta de o fazer para o seu ambiente de desenvolvimento.
    """
    # --- Usa ModbusSlaveContext para um servidor simples e padrão ---
    # O dispositivo terá 10 holding registers com valores de 100 a 109 para teste.

    store1 = ModbusDeviceContext(hr=ModbusSequentialDataBlock(0, [0]*10)) 
    store2 = ModbusDeviceContext(hr=ModbusSequentialDataBlock(0, [100 + i for i in range(5)])) 
    context = ModbusServerContext(devices={1: store1, 2: store2}, single=False)

    identity = ModbusDeviceIdentification()
    identity.VendorName = 'Simulated CLP'
    identity.ProductCode = 'SIM'
    identity.VendorUrl = 'http://localhost'
    identity.ProductName = 'SimCLP'
    identity.ModelName = 'SimCLP v1'
    identity.MajorMinorRevision = '1.0'

    logger.info("Servidor Modbus TCP (Modo Single/Síncrono) a rodar em 127.0.0.1:5020")
    # Usa o servidor síncrono, que é mais estável para este cenário
    StartTcpServer(context=context, identity=identity, address=("127.0.0.1", 5020))

# --- Main ---
if __name__ == "__main__":
    threading.Thread(target=simulation, daemon=True).start()
    logger.info("A aguardar o servidor Modbus iniciar...")
    time.sleep(1)
    
    polling_service.start_all_from_controller()

    logger.info("Servidor Flask a rodar em 0.0.0.0:5000")
    # use_reloader=False é crucial para evitar que a thread do Modbus seja reiniciada incorretamente
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)


