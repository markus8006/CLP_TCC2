import json
import threading
import os

from src.views import create_app
from src.utils.network.discovery import run_full_discovery
from src.controllers.clp_controller import ClpController
from src.utils.root.paths import DISCOVERY_FILE
from src.utils.log.log import setup_logger

logger = setup_logger()

app = create_app()


def discovery_background_once():
    """
Executa o scanner em background e salva os resultados em JSON.
    """
    logger.info({"evento": "Iniciando descoberta de CLPs"})
    try:
        discovery_data = run_full_discovery()

        with open(DISCOVERY_FILE, "w") as f:
            json.dump(discovery_data, f, indent=2)

        logger.info({
            "evento": "Scanner finalizado",
            "detalhes": {"total_dispositivos": len(discovery_data)}
        })

    except Exception as e:
        logger.error({
            "evento": "Erro na descoberta de CLPs",
            "detalhes": {"erro": str(e)}
        })


if __name__ == "__main__":

    
    t = threading.Thread(target=discovery_background_once, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
