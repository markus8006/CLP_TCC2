# src/simulations/simulation.py
import asyncio
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSequentialDataBlock
from pymodbus.server import StartAsyncTcpServer
from pymodbus.device import ModbusDeviceIdentification
from src.utils.log.log import setup_logger

logger = setup_logger()

async def start_modbus_async(host: str = "127.0.0.1", port: int = 5020):
    # Cria blocos de dados (addresses a partir de 0)
    hr_block_1 = ModbusSequentialDataBlock(0, [0] * 10)                 # slave 1
    hr_block_2 = ModbusSequentialDataBlock(0, [100 + i for i in range(5)])  # slave 2

    # Cada slave precisa ser um ModbusSlaveContext
    slave1 = ModbusSlaveContext(hr=hr_block_1)
    slave2 = ModbusSlaveContext(hr=hr_block_2)

    # Cria o contexto do servidor com os slaves (unit ids)
    context = ModbusServerContext(slaves={1: slave1, 2: slave2}, single=False)

    identity = ModbusDeviceIdentification(
        info_name={
            "VendorName": "Simulated CLP",
            "ProductCode": "SIM",
            "ProductName": "SimCLP",
            "MajorMinorRevision": "1.0"
        }
    )

    logger.info("Iniciando servidor Modbus TCP em %s:%s", host, port)
    await StartAsyncTcpServer(context=context, identity=identity, address=(host, port))


def start_modbus_simulator(host: str = "127.0.0.1", port: int = 5020):
    """
    Função de entrada que pode ser chamada dentro de uma thread.
    StartAsyncTcpServer é async, então rodamos com asyncio.run()
    """
    try:
        asyncio.run(start_modbus_async(host, port))
    except Exception as e:
        logger.exception("Erro iniciando simulador Modbus: %s", e)



def add_register_test(name="CLP De Teste", address=0):
    from src.db import db
    from src.models.PLC import PLC
    from src.models.Registers import Register

# Supondo que já existe um PLC cadastrado
    plc = db.session.query(PLC).filter_by(name=name).first()
    if not plc:
        raise ValueError("Cadastre um PLC primeiro!")

    reg = Register(
    plc_id=plc.id,
    name="Temperatura Teste",
    address=address,                   # Endereço Modbus a ser lido (ex: 0 ou o usado pelo CLP real/simulador)
    register_type="holding",     # holding/input/coil/discrete
    data_type="int16",           # conforme seu CLP/simulador
    scale_factor=1.0,
    offset=0.0,
    unit="°C",
    is_active=True
    )
    db.session.add(reg)
    db.session.commit()
    print("Registrador salvo!")
