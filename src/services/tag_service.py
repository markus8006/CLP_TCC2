# src/services/tag_service.py
import json
import os
from src.models.Tag import Tag
from src.utils.root.root import get_project_root

PROJECT_ROOT = get_project_root()
TAGS_FILE = os.path.join(PROJECT_ROOT, "data/tags.json")

class TagService:
    @staticmethod
    def _carregar_tags():
        if not os.path.exists(TAGS_FILE):
            return []
        try:
            with open(TAGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [Tag.from_dict(item) for item in data]
        except (json.JSONDecodeError, IOError):
            return []

    @staticmethod
    def _salvar_tags(tags):
        with open(TAGS_FILE, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in tags], f, indent=4, ensure_ascii=False)

    @classmethod
    def listar(cls):
        return cls._carregar_tags()

    @classmethod
    def adicionar(cls, nome: str):
        tags = cls._carregar_tags()
        if not any(t.nome == nome for t in tags):
            nova = Tag(nome=nome)
            tags.append(nova)
            cls._salvar_tags(tags)
            return nova
        return None
