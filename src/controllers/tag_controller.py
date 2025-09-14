# src/controllers/tag_controller.py
from src.services.tag_service import TagService

class TagController:
    @staticmethod
    def listar_tags():
        return [tag.to_dict() for tag in TagService.listar()]

    @staticmethod
    def adicionar_tag(nome: str):
        tag = TagService.adicionar(nome)
        return tag.to_dict() if tag else None
