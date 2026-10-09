import requests
from datetime import datetime, timezone

URL = "https://arctic-shift.photon-reddit.com/api/posts/search"

# Posts do r/GTA6 publicados entre há 3 e há 2 dias
# (o Arctic Shift só atualiza os upvotes cerca de 36h depois de o post sair)
params = {
    "subreddit": "GTA6",
    "after": "3d",
    "before": "2d",
    "limit": "auto",  # devolve entre 100 e 1000 posts
    "fields": "id,title,score,num_comments,created_utc",
}

resposta = requests.get(URL, params=params, timeout=60)
resposta.raise_for_status()
posts = resposta.json()["data"]

print(f"{len(posts)} posts recolhidos\n")

# Ordena pelos mais votados e mostra os 10 primeiros
top = sorted(posts, key=lambda p: p["score"], reverse=True)[:10]

for p in top:
    data = datetime.fromtimestamp(p["created_utc"], tz=timezone.utc).strftime("%d/%m %H:%M")
    print(f"[{data}] {p['score']:>5} pts | {p['num_comments']:>4} coment. | {p['title']}")
    print(f"        https://reddit.com/r/GTA6/comments/{p['id']}\n")
