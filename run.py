# /run.py
from clp_app import create_app
from utils.discovery import run_full_discovery, save_discoveries_to_json
from utils.clp_manager import criar_clp
import json

app = create_app()

import threading

def discovery_background():
    save_discoveries_to_json(run_full_discovery(passive_timeout=10))

if __name__ == '__main__':
    threading.Thread(target=discovery_background, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=True)
