"""
Recolha diária do Radar GTA VI.

Corre sozinha no GitHub Actions todas as manhãs. Também podes correr à mão: clica no ▶.
1) Google News: notícias das últimas 48 horas sobre o GTA VI
2) Reddit (via Arctic Shift): publicações e comentários por dia no r/GTA6
3) Gera o ficheiro docs/dados.js que o site lê

Se uma fonte falhar, as outras continuam e o site usa os últimos dados guardados.
Não usa o Media Cloud (a quota fica livre para a tese).
"""
import csv
import json
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "collector" / "site"))
import gerar_dados  # noqa: E402

PASTA_NOTICIAS = RAIZ / "data" / "noticias"
PASTA_REDDIT = RAIZ / "data" / "reddit"
CABECALHOS = {"User-Agent": "Mozilla/5.0 (radar-gta-vi; projeto pessoal de fas)"}


def pedir(url, params=None, tentativas=3, espera=20):
    """GET com até 3 tentativas. Devolve a resposta ou None."""
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = requests.get(url, params=params, headers=CABECALHOS, timeout=90)
            if resposta.status_code == 200:
                return resposta
            motivo = f"código {resposta.status_code}"
        except requests.RequestException as erro:
            motivo = type(erro).__name__
        print(f"   tentativa {tentativa}/{tentativas} falhou ({motivo})")
        if tentativa < tentativas:
            time.sleep(espera)
    return None


def recolher_noticias():
    print("1/3  Google News (últimas 48 horas)...")
    resposta = pedir("https://news.google.com/rss/search", {
        "q": '"GTA 6" OR "GTA VI" when:2d', "hl": "en-US", "gl": "US", "ceid": "US:en"})
    if resposta is None:
        print("     Sem resposta. O site continua com a última recolha.")
        return False

    artigos, vistos = [], set()
    for item in ET.fromstring(resposta.content).iter("item"):
        data_texto = item.findtext("pubDate")
        fonte_el = item.find("source")
        if not data_texto or fonte_el is None:
            continue
        fonte = (fonte_el.text or "").strip()
        titulo = (item.findtext("title") or "").strip()
        if titulo.endswith(f" - {fonte}"):
            titulo = titulo[: -len(f" - {fonte}")]
        chave = (titulo.lower(), fonte.lower())
        if not titulo or chave in vistos:  # o Google repete às vezes a mesma notícia
            continue
        vistos.add(chave)
        artigos.append({
            "t": titulo,
            "s": fonte,
            "u": fonte_el.get("url", ""),
            "d": parsedate_to_datetime(data_texto).astimezone(timezone.utc).isoformat(timespec="seconds"),
            "link": item.findtext("link") or "",
        })

    agora = datetime.now(timezone.utc)
    snapshot = {"recolhido": agora.isoformat(timespec="seconds"), "artigos": artigos}
    PASTA_NOTICIAS.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(snapshot, ensure_ascii=False, indent=1)
    (PASTA_NOTICIAS / f"{agora:%Y-%m-%d}.json").write_text(texto, encoding="utf-8")
    (PASTA_NOTICIAS / "ultimo.json").write_text(texto, encoding="utf-8")

    # Uma linha por dia com a divisão por tipo de site (para ver a evolução do "spillover")
    fontes = gerar_dados.carregar_fontes()
    contagem = {"gaming": 0, "cultura": 0, "geral": 0, "outros": 0}
    for a in artigos:
        contagem[gerar_dados.classificar(a["s"], a["u"], fontes)] += 1
    ficheiro = PASTA_NOTICIAS / "composicao.csv"
    linhas = {}
    if ficheiro.exists():
        with ficheiro.open(encoding="utf-8", newline="") as f:
            for linha in csv.DictReader(f):
                linhas[linha["data"]] = linha
    linhas[f"{agora:%Y-%m-%d}"] = {"data": f"{agora:%Y-%m-%d}", "total": len(artigos), **contagem}
    with ficheiro.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=["data", "total", "gaming", "cultura", "geral", "outros"])
        escritor.writeheader()
        for d in sorted(linhas):
            escritor.writerow(linhas[d])

    print(f"     {len(artigos)} notícias guardadas")
    return True


def recolher_reddit():
    print("2/3  Reddit r/GTA6 (publicações e comentários por dia)...")
    series = {}
    for nome, chave in (("posts", "r/GTA6/posts/count"), ("comments", "r/GTA6/comments/count")):
        resposta = pedir("https://arctic-shift.photon-reddit.com/api/time_series",
                         {"key": chave, "precision": "day", "after": "2023-11-01"})
        if resposta is None:
            print("     Sem resposta do Arctic Shift. O site continua com os dados anteriores.")
            return False
        pontos = resposta.json().get("data") or []
        series[nome] = {
            datetime.fromtimestamp(p["date"], tz=timezone.utc).date().isoformat(): p["value"] for p in pontos
        }
    if not series["posts"]:
        print("     Resposta vazia. O site continua com os dados anteriores.")
        return False

    PASTA_REDDIT.mkdir(parents=True, exist_ok=True)
    with (PASTA_REDDIT / "r_gta6_diario.csv").open("w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(["data", "publicacoes", "comentarios"])
        for d in sorted(set(series["posts"]) | set(series["comments"])):
            escritor.writerow([d, series["posts"].get(d, ""), series["comments"].get(d, "")])
    print(f"     {len(series['posts'])} dias guardados")
    return True


if __name__ == "__main__":
    ok_noticias = recolher_noticias()
    ok_reddit = recolher_reddit()
    print("3/3  A gerar os dados do site...")
    gerar_dados.main()
    print("\nFeito." + ("" if ok_noticias and ok_reddit else " (Uma das fontes falhou; ver acima.)"))
