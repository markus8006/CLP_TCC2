from src.views import create_app
from src.utils.async_runner import AsyncLoopThread
from src.services.polling_service import PollingService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cria instância do loop asyncio em thread separada
async_loop = AsyncLoopThread()

# Instância do PollingService
polling_service = PollingService()

# Cria src Flask
src = create_app()

# Injeta o async_loop no polling_service se necessário
# polling_service.set_async_loop(async_loop)

# Inicializa PollingService no loop asyncio sem bloquear o run.py
try:
    async_loop.run_coro(polling_service.start_polling())
    logger.info("PollingService iniciado em background")
except Exception as e:
    logger.error(f"Erro ao iniciar PollingService: {e}")

if __name__ == '__main__':
    # Roda o Flask normalmente (debug=False para produção)
    src.run(host='0.0.0.0', port=5000, debug=True)
