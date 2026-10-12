"""
Recolha ÚNICA do Media Cloud: atenção dos media ao GTA VI desde antes do 1.º trailer.

- Gasta cerca de 15 pedidos da tua quota semanal (10 000). Não corre automaticamente.
- Cada resposta fica guardada em data/mediacloud/cache: se correres outra vez,
  só pede o que ainda falta (não gasta quota a repetir).
- Se o Media Cloud disser "rate limited", o script espera e tenta outra vez sozinho.
- A chave está no ficheiro .env, que nunca vai para o GitHub.
- Para correr: clica no botão ▶ no canto superior direito do VS Code.
"""
import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "data" / "mediacloud"
CACHE = PASTA / "cache"

QUERY = '"GTA 6" OR "GTA VI" OR "Grand Theft Auto 6" OR "Grand Theft Auto VI"'
INICIO = date(2023, 11, 1)  # um mês antes do 1.º trailer (5 dez 2023)
FIM = date(2026, 10, 10)    # fixo, para a cache funcionar entre execuções
MAX_PICOS = 12

# Coleções de imprensa nacional (IDs encontrados na 1.ª execução)
COLECOES = {
    "United States": 34412234,
    "United Kingdom": 34412476,
    "Portugal": 34412337,
    "Brazil": 34412257,
}

BASE = "https://search.mediacloud.org/api/"
ESPACO_ENTRE_PEDIDOS = 15  # segundos
ESPERA_SE_LIMITADO = 90    # segundos
MAX_TENTATIVAS = 5
pedidos = 0


def ler_chave():
    ficheiro = RAIZ / ".env"
    if ficheiro.exists():
        for linha in ficheiro.read_text(encoding="utf-8").splitlines():
            if linha.startswith("MEDIACLOUD_API_KEY="):
                return linha.split("=", 1)[1].strip()
    print("Falta a chave do Media Cloud no ficheiro .env")
    sys.exit(1)


sessao = requests.Session()
sessao.headers.update({"Authorization": f"Token {ler_chave()}", "Accept": "application/json"})


def pedir(endpoint, params):
    """Pede ao Media Cloud, usando a cache se já tivermos esta resposta."""
    global pedidos
    chave = hashlib.md5(json.dumps([endpoint, params], sort_keys=True).encode()).hexdigest()
    ficheiro = CACHE / f"{endpoint.replace('/', '_')}_{chave}.json"
    if ficheiro.exists():
        return json.loads(ficheiro.read_text(encoding="utf-8"))

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        if pedidos > 0:
            time.sleep(ESPACO_ENTRE_PEDIDOS)
        pedidos += 1
        resposta = sessao.get(BASE + endpoint, params=params, timeout=180)
        if resposta.status_code == 200:
            dados = resposta.json()
            ficheiro.write_text(json.dumps(dados), encoding="utf-8")
            return dados
        if resposta.status_code == 429 and tentativa < MAX_TENTATIVAS:
            print(f"     Limite temporário do Media Cloud. A esperar {ESPERA_SE_LIMITADO} s "
                  f"(tentativa {tentativa}/{MAX_TENTATIVAS})...")
            time.sleep(ESPERA_SE_LIMITADO)
            continue
        print(f"\nErro {resposta.status_code} em {endpoint}: {resposta.text[:300]}")
        print(f"Pedidos usados nesta execução: {pedidos}. O que já foi recolhido ficou guardado;")
        print("podes voltar a carregar no ▶ mais tarde e ele continua de onde parou.")
        sys.exit(1)


def params_pesquisa(colecoes, inicio=INICIO, fim=FIM):
    return {
        "q": QUERY,
        "start": inicio.isoformat(),
        "end": fim.isoformat(),
        "platform": "onlinenews-mediacloud",
        "cs": ",".join(str(c) for c in colecoes),
    }


CACHE.mkdir(parents=True, exist_ok=True)
pd.DataFrame([{"pais": p, "colecao_id": i} for p, i in COLECOES.items()]).to_csv(
    PASTA / "colecoes.csv", index=False)

# 1) Volume diário de notícias por país
print("1/3  A recolher o volume diário de notícias por país...")
linhas = []
for pais, cid in COLECOES.items():
    dados = pedir("search/count-over-time", params_pesquisa([cid]))
    for ponto in dados["count_over_time"]["counts"]:
        linhas.append({"pais": pais, **ponto})
    print(f"     {pais}: ok")
volume = pd.DataFrame(linhas)
volume["date"] = pd.to_datetime(volume["date"]).dt.date
volume.to_csv(PASTA / "volume_diario.csv", index=False)

# 2) Que meios mais escreveram sobre o GTA VI
print("2/3  A recolher os meios que mais escreveram...")
dados = pedir("search/sources", params_pesquisa(COLECOES.values()))  # o servidor não aceita "limit" aqui
pd.DataFrame(dados["sources"]).head(30).to_csv(PASTA / "fontes_top.csv", index=False)

# 3) Radar de Picos: dias com o dobro (ou mais) da média da semana anterior
print("3/3  A detetar picos e a recolher as manchetes desses dias...")
diario = volume.groupby("date")["count"].sum().sort_index()
diario.index = pd.to_datetime(diario.index)
diario = diario.asfreq("D", fill_value=0)
media_semana = diario.shift(1).rolling(7, min_periods=3).mean()
multiplicador = diario / media_semana.clip(lower=1)
candidatos = pd.DataFrame({"noticias": diario, "media_7d": media_semana.round(1),
                           "multiplicador": multiplicador.round(1)})
candidatos = candidatos[(candidatos["noticias"] >= 10) & (candidatos["multiplicador"] >= 2)]

picos = []
for dia, _ in candidatos.sort_values("noticias", ascending=False).iterrows():
    if all(abs((dia - p).days) > 3 for p in picos):  # um pico por acontecimento
        picos.append(dia)
    if len(picos) == MAX_PICOS:
        break

tabela_picos = candidatos.loc[sorted(picos)].reset_index(names="date")
tabela_picos["date"] = tabela_picos["date"].dt.date
tabela_picos.to_csv(PASTA / "picos.csv", index=False)

manchetes = []
for dia in tabela_picos["date"]:
    dados = pedir("search/story-list",
                  {**params_pesquisa(COLECOES.values(), dia, dia), "page_size": 50})
    for h in dados.get("stories", []):
        manchetes.append({"date": dia, "title": h.get("title"), "media_name": h.get("media_name"),
                          "url": h.get("url"), "language": h.get("language")})
pd.DataFrame(manchetes).to_csv(PASTA / "picos_manchetes.csv", index=False)

# Resumo
print(f"\nFeito! Pedidos usados nesta execução: {pedidos} (de 10 000 por semana)")
print(f"Dados guardados em: {PASTA}\n")
print("=== Picos detetados ===")
for _, p in tabela_picos.iterrows():
    titulos = [m["title"] for m in manchetes if m["date"] == p["date"] and m["title"]][:2]
    print(f"\n{p['date']:%d/%m/%Y}  {int(p['noticias'])} notícias ({p['multiplicador']}x a média)")
    for t in titulos:
        print(f"   - {t}")
