import os
from src.utils.root.root import get_project_root

# Raiz do projeto
PROJECT_ROOT = get_project_root()

# Pasta de dados centralizada
DATA_DIR = os.path.join(PROJECT_ROOT, "src", "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Arquivos JSON
DEVICES_FILE = os.path.join(DATA_DIR, "devices.json")
DISCOVERY_FILE = os.path.join(DATA_DIR, "discovery_results.json")
CLPS_FILE = os.path.join(DATA_DIR, "clps.json")
TAGS_FILE = os.path.join(DATA_DIR, "tags.json")