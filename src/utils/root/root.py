import os, sys

def get_project_root():
    """
    Retorna o caminho raiz do projeto, funcionando tanto em modo de
    desenvolvimento (.py) quanto em modo de produção (.exe).
    """
    if hasattr(sys, '_MEIPASS'):
        # Estamos rodando em um executável criado pelo PyInstaller
        # _MEIPASS é o caminho para a pasta temporária onde tudo foi extraído
        return sys._MEIPASS
    else:
        # Estamos rodando como um script normal.
        # __file__ está em /utils/clp_manager.py, então subimos dois níveis
        # para chegar na raiz do projeto.
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))