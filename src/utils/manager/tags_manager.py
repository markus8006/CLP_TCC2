# utils/tags_manager.py
import json
import os
from utils.root import get_project_root

PROJECT_ROOT = get_project_root()
TAGS_FILE = os.path.join(PROJECT_ROOT, "data/tags.json")

def _carregar_tags():
    if not os.path.exists(TAGS_FILE):
        return []
    try:
        with open(TAGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def _salvar_tags(tags):
    with open(TAGS_FILE, "w", encoding="utf-8") as f:
        json.dump(tags, f, indent=4, ensure_ascii=False)

tags_globais = _carregar_tags()

def adicionar_tag_global(tag):
    if tag not in tags_globais:
        tags_globais.append(tag)
        _salvar_tags(tags_globais)
        return True
    return False