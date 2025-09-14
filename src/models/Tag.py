class Tag:
    def __init__(self, nome: str):
        self.nome = nome

    def to_dict(self):
        return {"nome": self.nome}

    @staticmethod
    def from_dict(data: dict):
        return Tag(nome=data["nome"])
