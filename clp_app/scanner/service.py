import socket
import threading
import queue
from utils import clp_manager
from utils import network
from utils import discovery 

PORTAS_CLP_COMUNS = [502, 44818, 102]
NUM_THREADS_SCANNER = 50

class ScannerService:
    def __init__(self):
        self.tarefas_queue = queue.Queue()
        self.resultados_queue = queue.Queue()
        self._is_running = False
        self._status_message = "Parado."
        # Mantém as threads vivas para reutilização
        self._threads = []
        self._consumidor_thread = None
        self._start_threads() # Inicia as threads uma vez

    def _start_threads(self):
        """Inicia os threads consumidores e trabalhadores em background."""
        # Inicia o consumidor
        self._consumidor_thread = threading.Thread(target=self._consumidor, daemon=True)
        self._consumidor_thread.start()
        # Inicia os trabalhadores
        for _ in range(NUM_THREADS_SCANNER):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            self._threads.append(t)

    def _worker(self):
        """Trabalhador que executa o port scan."""
        while True:
            ip, porta = self.tarefas_queue.get()
            if ip is None: # Sinal para parar
                break
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                if sock.connect_ex((ip, porta)) == 0:
                    self.resultados_queue.put(ip)
                sock.close()
            finally:
                self.tarefas_queue.task_done()

    def _consumidor(self):
        """Consumidor que salva os CLPs encontrados."""
        ips_encontrados_nesta_sessao = set()
        while True:
            ip = self.resultados_queue.get()
            if ip is None: # Sinal para parar
                break

            if ip not in ips_encontrados_nesta_sessao:
                ips_encontrados_nesta_sessao.add(ip)
                if not clp_manager.buscar_por_ip(ip):
                    print(f"NOVO CLP IDENTIFICADO: {ip}")
                    sub_rede = network.get_subnet_from_ip(ip)
                    clp_manager.criar_clp(ip, grupo=sub_rede)
            self.resultados_queue.task_done()
    
    # Dentro da classe ScannerService, em /scanner/service.py

    def _run_full_discovery_task(self):
        """A tarefa que será executada em uma thread separada."""
        self._status_message = "Fase 1/2: Descoberta passiva e ativa de IPs..."
        
        # Executa a descoberta com Scapy para obter a lista de alvos
        # MODIFICADO: Agora recebe uma lista de dicionários
        discovered_devices = discovery.run_full_discovery(passive_timeout=60)
        
        if discovered_devices is None: # Erro de permissão
            self._status_message = "Erro de Permissão. Execute como Administrador."
            self._is_running = False
            return
        
        if not discovered_devices:
            self._status_message = "Nenhum IP ativo encontrado na rede."
            self._is_running = False
            return
            
        # NOVO: Salva o resultado detalhado em um arquivo JSON
        discovery.save_discoveries_to_json(discovered_devices)
        
        # Extrai apenas os IPs da lista de dicionários para o port scanner
        ips_para_escanear = [device['ip'] for device in discovered_devices]

        # Fase 3: Alimenta a fila de port scan com os IPs encontrados
        self._status_message = f"Fase 2/2: Identificando CLPs em {len(ips_para_escanear)} IPs..."
        for ip in ips_para_escanear:
            for porta in PORTAS_CLP_COMUNS:
                self.tarefas_queue.put((ip, porta))
        
        self.tarefas_queue.join()
        self.resultados_queue.join()
        
        self._status_message = "Rotina de descoberta concluída."
        self._is_running = False
        print("[*] Rotina de descoberta concluída.")

    # ESTA É A SUA NOVA FUNÇÃO PRINCIPAL
    def iniciar_rotina_completa(self):
        """Inicia toda a rotina de descoberta e identificação em background."""
        if self._is_running:
            print("Uma rotina já está em execução.")
            return False
            
        self._is_running = True
        print("Iniciando rotina completa de descoberta em background...")
        
        # Executa a tarefa pesada em uma nova thread para não travar a aplicação
        discovery_thread = threading.Thread(target=self._run_full_discovery_task, daemon=True)
        discovery_thread.start()
        
        return True

    def get_status(self):
        """Retorna a mensagem de status atual."""
        return self._status_message

# Instância única do serviço
scanner_service = ScannerService()

if __name__ == "__main__":
    scanner_service._run_full_discovery_task()