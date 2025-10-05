from pymodbus.datastore import ModbusDeviceContext, ModbusServerContext, ModbusSequentialDataBlock
from pymodbus.pdu.device import ModbusDeviceIdentification
from pymodbus.server import StartTcpServer
from src.utils.log.log import setup_logger



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