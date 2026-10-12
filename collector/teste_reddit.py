"""
Teste: os 10 posts mais votados do r/GTA6 de há 2 dias, via Arctic Shift.
Para correr: clica no botão ▶ no canto superior direito do VS Code.
"""
import sys
import time
from datetime import datetime, timezone

import requests

URL = "https://arctic-shift.photon-reddit.com/api/posts/search"

# Posts do r/GTA6 publicados entre há 3 e há 2 dias
# (o Arctic Shift só atualiza os upvotes cerca de 36h depois de o post sair)
PARAMS = {
    "subreddit": "GTA6",
    "after": "3d",
    "before": "2d",
    "limit": 100,
    "fields": "id,title,score,num_comments,created_utc",
}

TENTATIVAS = 3
ESPERA = 15  # segundos entre tentativas


def buscar_posts():
    """Pede os posts ao Arctic Shift; se o servidor falhar, tenta até 3 vezes."""
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resposta = requests.get(URL, params=PARAMS, timeout=60)
            if resposta.status_code == 200:
                dados = resposta.json()
                if dados.get("data") is not None:
                    return dados["data"]
                motivo = dados.get("error") or "resposta vazia"
            else:
                motivo = f"código {resposta.status_code}"
        except requests.RequestException as erro:
            motivo = type(erro).__name__
        print(f"Tentativa {tentativa}/{TENTATIVAS} falhou ({motivo}).")
        if tentativa < TENTATIVAS:
            print(f"A tentar outra vez daqui a {ESPERA} segundos...")
            time.sleep(ESPERA)
    return None


posts = buscar_posts()

if posts is None:
    print("\nO servidor do Arctic Shift não está a responder neste momento.")
    print("Não é um erro do teu código nem do teu PC. Tenta outra vez mais tarde.")
    sys.exit(1)

print(f"{len(posts)} posts recolhidos\n")

# Ordena pelos mais votados e mostra os 10 primeiros
top = sorted(posts, key=lambda p: p["score"], reverse=True)[:10]

for p in top:
    data = datetime.fromtimestamp(p["created_utc"], tz=timezone.utc).strftime("%d/%m %H:%M")
    print(f"[{data}] {p['score']:>5} pts | {p['num_comments']:>4} coment. | {p['title']}")
    print(f"        https://reddit.com/r/GTA6/comments/{p['id']}\n")
