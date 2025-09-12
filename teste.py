import requests

url = "http://127.0.0.1:5000/192.168.0.10/connect"  # ajuste o IP e porta se necessário

data = {
    "port": 502  # substitua pela porta que você quer usar
}

try:
    response = requests.post(url, json=data)
    print("Status code:", response.status_code)
    print("Resposta:", response.json())
except Exception as e:
    print("Erro ao chamar a API:", e)
