import subprocess
import re
import shutil
  

try:
    from scapy.all import sr1, IP, TCP, conf
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

def _parse_nmap_output(output: str) -> list[int]:
    """Extrai portas abertas do output do nmap (lista de ints)."""
    portas_abertas = re.findall(r'(\d+)/tcp\s+open', output)
    return sorted({int(p) for p in portas_abertas})

def _scapy_syn_check(ip: str, ports, timeout=1) -> list[int]:
    """Fallback com Scapy: envia SYN e espera SYN-ACK. Retorna lista de portas abertas."""
    if not SCAPY_AVAILABLE:
        print("Scapy não disponível para fallback.")
        return []

    conf.verb = 0
    abertas = []
    for p in ports:
        try:
            pkt = IP(dst=ip)/TCP(dport=int(p), flags="S")
            resp = sr1(pkt, timeout=timeout, verbose=False)
            # Se a resposta for um pacote TCP com a flag SYN-ACK (0x12), a porta está aberta.
            if resp and resp.haslayer(TCP) and resp[TCP].flags & 0x12:
                abertas.append(int(p))
        except Exception as e:
            print(f"Erro no scapy-syn check para {ip}:{p} -> {e}")
    return sorted(set(abertas))






def escanear_portas(ip: str, intervalo: int = 1000, timeout: int = 60, portas_alvo: list = None) -> list[int]:
    """
    Escaneia portas abertas via nmap (ou fallback Scapy) e RETORNA uma lista de portas.
    """
    print(f"Iniciando escaneamento de portas para o IP: {ip}...")

    ports_to_check_str = ""
    if portas_alvo:
        ports_to_check_str = ",".join(map(str, sorted({int(p) for p in portas_alvo})))
    else:
        ports_to_check_str = f"1-{int(intervalo)}"

    portas_encontradas = []
    nmap_path = shutil.which("nmap")

    if nmap_path:
        cmd = [nmap_path, '-sT', '-n', '-T4', '-p', ports_to_check_str, ip]
        try:
            print(f"Executando nmap: {' '.join(cmd)}")
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
            if proc.returncode == 0:
                portas_encontradas = _parse_nmap_output(proc.stdout)
            else:
                print(f"Nmap retornou código {proc.returncode} para {ip}. stderr: {proc.stderr}")
        except subprocess.TimeoutExpired:
            print(f"Nmap expirou (timeout) ao escanear {ip}")
        except Exception as e:
            print(f"Erro inesperado ao executar nmap para {ip}: {e}")

    # Se nmap falhou ou não encontrou nada, tenta o fallback com Scapy se portas específicas foram dadas
    if not portas_encontradas and portas_alvo:
        print(f"Nmap não encontrou portas em {ip}. Tentando fallback com Scapy para {portas_alvo}.")
        portas_encontradas = _scapy_syn_check(ip, portas_alvo)
    
    if portas_encontradas:
        print(f"SUCESSO: Portas abertas encontradas em {ip}: {portas_encontradas}")
    else:
        print(f"Nenhuma porta aberta encontrada em {ip} com os métodos utilizados.")
        
    return portas_encontradas