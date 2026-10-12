"""
Teste: as notícias mais recentes sobre o GTA VI (Google News, últimas 48 horas).
Não precisa de chave nem de conta.
Para correr: clica no botão ▶ no canto superior direito do VS Code.
"""
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from email.utils import parsedate_to_datetime

import requests

URL = "https://news.google.com/rss/search"
PARAMS = {
    "q": '"GTA 6" OR "GTA VI" when:2d',  # when:2d = últimas 48 horas
    "hl": "en-US",
    "gl": "US",
    "ceid": "US:en",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (projeto pessoal gta6-hype)"}

try:
    resposta = requests.get(URL, params=PARAMS, headers=HEADERS, timeout=30)
    resposta.raise_for_status()
except requests.RequestException as erro:
    print(f"Não consegui ligar ao Google News ({type(erro).__name__}).")
    print("Tenta outra vez daqui a pouco.")
    sys.exit(1)

# O Google News devolve um ficheiro RSS (XML): cada notícia é um <item>
raiz = ET.fromstring(resposta.content)
noticias = []
for item in raiz.iter("item"):
    data_texto = item.findtext("pubDate")
    if not data_texto:
        continue
    fonte = item.findtext("source", default="?")
    titulo = item.findtext("title", default="")
    # O título vem como "Título - Fonte"; tiramos a fonte do fim
    if titulo.endswith(f" - {fonte}"):
        titulo = titulo[: -len(f" - {fonte}")]
    noticias.append({
        "titulo": titulo,
        "fonte": fonte,
        "data": parsedate_to_datetime(data_texto).astimezone(),  # hora de Portugal
        "link": item.findtext("link"),
    })

noticias.sort(key=lambda n: n["data"], reverse=True)

print(f"{len(noticias)} notícias sobre o GTA VI nas últimas 48 horas\n")

print("=== As 15 mais recentes ===\n")
for n in noticias[:15]:
    print(f"[{n['data']:%d/%m %H:%M}] {n['titulo']}")
    print(f"              {n['fonte']}\n")

print("=== Quem mais escreveu sobre o GTA VI ===\n")
for fonte, total in Counter(n["fonte"] for n in noticias).most_common(10):
    print(f"{total:>3}  {fonte}")
