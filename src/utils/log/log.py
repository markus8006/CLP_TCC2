import logging
from colorama import Fore, Style, init

init(autoreset=True)  # reseta cores automaticamente

class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, Fore.WHITE)
        log_fmt = f"[%(asctime)s] {record.levelname:<8} %(message)s"
        formatter = logging.Formatter(log_fmt, "%Y-%m-%d %H:%M:%S")
        return color + formatter.format(record) + Style.RESET_ALL

def setup_logger():
    logger = logging.getLogger()
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        handler.setFormatter(ColorFormatter())
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
    return logger

# Uso
# logger = setup_logger()
# logger.info("Iniciando descoberta de CLPs")
# logger.warning("Nenhum dispositivo respondeu na sub-rede 192.168.0.0/24")
# logger.error("Erro durante scan ARP: Permissões insuficientes")
