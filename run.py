# run.py (substitua)
import logging
import threading
import time

from src.views import create_app
from src.utils.async_runner import async_loop     # IMPORTA a instância global, NÃO crie outra
from src.services.polling_service import PollingService
from src.simulations.simulation import start_modbus_simulator, add_register_test
from src.db import db
from src.models.PLC import PLC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

host = "127.0.0.1"
port = 5020

if __name__ == '__main__':
    app = create_app()

    # Cria PollingService e injeta a app (para usar app_context corretamente)
    polling_service = PollingService(app)

    # Inicia simulador Modbus em thread separada (start_modbus_simulator deve usar asyncio.run internamente)
    thread = threading.Thread(target=start_modbus_simulator, args=(host, port), daemon=True)
    thread.start()
    logger.info("Thread do simulador Modbus iniciada.")

    time.sleep(1)

    with app.app_context():
        try:
            add_register_test(name="CLP_S", address=0)
        except:
            pass

        plc = db.session.query(PLC).filter(PLC.ip_address == host).first()

        if plc:
            # Agende start_polling no loop global (async_loop importado acima)
            fut = async_loop.run_coro(polling_service.start_polling())
            logger.info("PollingService agendado: %s", fut)

            # aguarde um pouco e liste as tarefas conhecidas pela instância polling_service
            time.sleep(1)
            logger.info("Polling tasks keys (após agendar): %s", list(polling_service.polling_tasks.keys()))
        else:
            logger.error("PLC não encontrado para iniciar polling")

    # start Flask (use_reloader=False evita duplicar processos)
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
