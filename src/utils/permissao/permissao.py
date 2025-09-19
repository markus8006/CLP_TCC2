import os
import sys

def verificar_permissoes():
    # Windows -> checar admin
    if os.name == "nt":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    # Linux/Mac -> UID 0 = root
    else:
        return os.geteuid() == 0
