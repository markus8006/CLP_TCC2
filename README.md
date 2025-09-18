📘 CLP_TCC2

Sistema de descoberta e gerenciamento de CLPs na rede, com interface web e backend em Python.

🚀 Funcionalidades

🔍 Descoberta automática de CLPs na rede (via Scapy + ARP/TCP scan).

🌐 Interface web simples com Flask para visualizar e interagir.

👥 Gestão de usuários com roles (perfis de acesso).

📂 Armazenamento seguro em JSON (com escrita atômica).

📊 Logs estruturados em formato JSON (fáceis de analisar).

⚡ Extensível para integração futura com OPC UA.


```bash
📂 Estrutura do projeto
CLP_TCC2/
│── src/
│   ├── controllers/       # Lógica de controle (ex: ClpController)
│   ├── repositories/      # Repositórios (JSON, etc.)
│   ├── utils/             # Funções auxiliares (logging, discovery, etc.)
│   ├── views/             # Criação do app Flask
│── data/                  # Arquivos salvos (descobertas, configs)
│── run.py                 # Ponto de entrada do sistema
│── requirements.txt       # Dependências Python
│── Dockerfile             # Containerização do projeto
│── README.md              # Este arquivo
```

⚙️ Requisitos

Python 3.12+

Pipenv ou venv (recomendado)

Dependências do requirements.txt

🖥️ Como rodar localmente
1. Clonar o repositório
```bash
git clone https://github.com/seu-user/clp_tcc2.git
cd clp_tcc2

3. Criar ambiente virtual
python -m venv .venv
```

Ativar no Windows:
```bash
.venv\Scripts\activate
```


Ativar no Linux/Mac:

```bash
source .venv/bin/activate
```

3. Instalar dependências
```bash
pip install -r requirements.txt
```
5. Rodar aplicação
```bash
python run.py
```

Acesse em:
👉 http://localhost:5000

🐳 Rodando com Docker
Buildar imagem
```bash
docker build -t clp_tcc2 .
```

Rodar container
```bash
docker run -p 5000:5000 clp_tcc2
```

📊 Logs

Os logs são emitidos em JSON estruturado.
Exemplo:

```json
{
  "timestamp": "2025-09-18T17:45:12",
  "level": "INFO",
  "evento": "Scanner iniciado",
  "detalhes": {"interface": "eth0"}
}
```
🔮 Futuras melhorias

Integração completa com OPC UA.

Dashboard web mais avançado.

Autenticação JWT para usuários.

CI/CD no GitHub Actions.

✍️ Autor: Guilherme Rezende
📅 Ano: 2025


![python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow)
![License](https://img.shields.io/badge/License-MIT-green)


<p align="center">
  <img src="docs/logo.png" width="200">
</p>

