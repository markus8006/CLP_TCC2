import json
import logging
import threading
import os

from src.views import create_app
from src.utils.network.discovery import run_full_discovery
from src.controllers.clp_controller import ClpController
from src.utils.root.paths import DISCOVERY_FILE

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = create_app()

def discovery_background_once():
    """
    Executa o scanner uma vez, salva results em DISCOVERY_FILE
    e cria/atualiza dispositivos via ClpController.
    """
    try:
        logging.info("Iniciando descoberta de rede (scanner)...")
        results = run_full_discovery(passive_timeout=10)  # retorna lista de dicts

        # garante pasta (já criada em paths.py, mas sem problema)
        os.makedirs(os.path.dirname(DISCOVERY_FILE), exist_ok=True)

        # salva resultados
        with open(DISCOVERY_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logging.info(f"Descobertas salvas em: {DISCOVERY_FILE} (total {len(results)} itens)")

        # atualiza dispositivos via controller
        with app.app_context():
            for dado in results:
                try:
                    ClpController.criar(dado)
                except Exception:
                    logging.exception(f"Erro ao criar/atualizar dispositivo: {dado.get('ip')}")
        logging.info("Processamento das descobertas finalizado.")

    except Exception:
        logging.exception("Falha durante execução do scanner.")

if __name__ == "__main__":

    
    t = threading.Thread(target=discovery_background_once, daemon=True)
    t.start()

    # evita duplicar scanner no debug
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
