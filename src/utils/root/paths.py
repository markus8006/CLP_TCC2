import os
from dotenv import load_dotenv
from src.utils.root.root import get_project_root

# Carregar variáveis do .env
load_dotenv()

# Raiz do projeto
PROJECT_ROOT = get_project_root()

# Diretório de dados
DATA_DIR = os.getenv("DATA_DIR", os.path.join(PROJECT_ROOT, "src", "data"))
os.makedirs(DATA_DIR, exist_ok=True)

# Arquivos JSON (junta DATA_DIR + nome do arquivo)
DEVICES_FILE = os.path.join(DATA_DIR, os.getenv("DEVICES_FILE", "devices.json"))
DISCOVERY_FILE = os.path.join(DATA_DIR, os.getenv("DISCOVERY_FILE", "discovery_results.json"))
CLPS_FILE = os.path.join(DATA_DIR, os.getenv("CLPS_FILE", "clps.json"))
TAGS_FILE = os.path.join(DATA_DIR, os.getenv("TAGS_FILE", "tags.json"))
