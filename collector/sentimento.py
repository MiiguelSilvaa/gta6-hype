"""
Hype vs Realidade: sentimento diário dos comentários do r/GTA6.

Para cada dia: uma amostra de comentários (6 janelas de 4 horas x 40 comentários),
classificados como positivo, neutro ou negativo por um modelo RoBERTa treinado em redes sociais
(cardiffnlp/twitter-roberta-base-sentiment-latest). Se o modelo não estiver disponível, usa o VADER.

Guarda APENAS totais por dia e por tema em data/sentimento/ (nunca o texto nem os autores).
Cada execução trata no máximo MAX_DIAS dias em falta, dos mais recentes para os mais antigos,
por isso o histórico desde nov 2023 vai sendo preenchido ao longo de vários dias.

Corre no GitHub Actions. Uso: python collector/sentimento.py [--max-dias 150]
"""
import argparse
import csv
import re
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "data" / "sentimento"
INICIO = date(2023, 11, 1)
URL = "https://arctic-shift.photon-reddit.com/api/comments/search"
JANELAS = 6           # janelas de 4 horas por dia
POR_JANELA = 40       # comentários por janela
CABECALHOS = {"User-Agent": "Mozilla/5.0 (radar-gta-vi; projeto pessoal de fas)"}
MODELO = "cardiffnlp/twitter-roberta-base-sentiment-latest"

# Temas (inglês, porque o r/GTA6 escreve em inglês)
ASPETOS = {
    "graficos": r"\b(graphics?|visuals?|lighting|textures?|ray[ -]?tracing|realism|realistic|photorealistic|draw distance)\b",
    "historia": r"\b(story|plot|narrative|characters?|jason|lucia|missions?|ending|cutscenes?|protagonists?)\b",
    "mapa": r"\b(map|vice city|leonida|open world|locations?|everglades|miami|keys|grassrivers|port gellhorn)\b",
    "preco": r"(\$\s?\d{2,3}\b|\b(price|pricing|priced|expensive|overpriced|cheap|preorders?|pre-orders?|ultimate edition|editions?|microtransactions?|shark cards?)\b)",
    "performance": r"\b(fps|frame ?rates?|30 ?fps|60 ?fps|performance|ps5 pro|optimi[sz]ation|optimi[sz]ed|stutter\w*|resolution)\b",
    "online": r"\b(gta online|online|multiplayer|roleplay|rp servers?|heists?)\b",
    "lancamento": r"\b(delay(ed|s)?|release date|launch(es|ed|ing)?|november|nov 19|pushed back|postpone[ds]?|release day)\b",
    "leaks": r"\b(leaks?|leaked|leaker|cyberleek|hack(er|ers|ed)?|dev build)\b",
}
REGEX = {k: re.compile(v, re.IGNORECASE) for k, v in ASPETOS.items()}
BOTS = {"automoderator", "[deleted]"}


def limpar(texto):
    linhas = [l for l in (texto or "").splitlines() if not l.strip().startswith(">")]  # tira citações
    texto = re.sub(r"https?://\S+", " ", " ".join(linhas))
    texto = re.sub(r"[*_~`#]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()[:600]


def pedir(params, tentativas=4):
    for tentativa in range(1, tentativas + 1):
        try:
            r = requests.get(URL, params=params, headers=CABECALHOS, timeout=90)
            if r.status_code == 200:
                dados = r.json()
                if dados.get("data") is not None:
                    return dados["data"]
            elif r.status_code == 429:
                espera = int(r.headers.get("X-RateLimit-Reset", "30") or 30)
                time.sleep(min(max(espera, 5), 120))
                continue
        except (requests.RequestException, ValueError):
            pass
        time.sleep(5 * tentativa)
    return None


def amostra_do_dia(dia):
    """Devolve a lista de textos do dia, ou None se o arquivo não respondeu."""
    textos, vistos = [], set()
    inicio = datetime(dia.year, dia.month, dia.day, tzinfo=timezone.utc)
    passo = timedelta(hours=24 // JANELAS)
    for j in range(JANELAS):
        a, b = inicio + j * passo, inicio + (j + 1) * passo
        dados = pedir({"subreddit": "GTA6", "after": int(a.timestamp()), "before": int(b.timestamp()),
                       "limit": POR_JANELA, "sort": "asc", "fields": "id,author,body"})
        if dados is None:
            return None
        for c in dados:
            corpo = c.get("body") or ""
            if c.get("id") in vistos or (c.get("author") or "").lower() in BOTS or corpo in ("[deleted]", "[removed]"):
                continue
            texto = limpar(corpo)
            if len(texto) >= 15:
                vistos.add(c.get("id"))
                textos.append(texto)
        time.sleep(0.6)
    return textos


class Classificador:
    def __init__(self, permitir_vader=False):
        self.nome = None
        try:
            from transformers import pipeline
            self._pipe = pipeline("sentiment-analysis", model=MODELO, tokenizer=MODELO,
                                  truncation=True, max_length=128)
            self.nome = "roberta"
        except Exception as erro:  # sem transformers/torch ou sem rede para o modelo
            if not permitir_vader:
                # Não misturamos modelos na mesma série: sem RoBERTa, não se faz nada hoje.
                raise SystemExit(f"Modelo RoBERTa indisponível ({type(erro).__name__}: {erro}).")
            print(f"   Modelo RoBERTa indisponível ({type(erro).__name__}); a usar VADER (só para testes).")
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self._vader = SentimentIntensityAnalyzer()
            self.nome = "vader"

    def __call__(self, textos):
        if not textos:
            return []
        if self.nome == "roberta":
            return [r["label"].lower() for r in self._pipe(textos, batch_size=32)]
        rotulos = []
        for t in textos:
            c = self._vader.polarity_scores(t)["compound"]
            rotulos.append("positive" if c >= 0.05 else "negative" if c <= -0.05 else "neutral")
        return rotulos


def ler(ficheiro):
    if not ficheiro.exists():
        return []
    with ficheiro.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def escrever(ficheiro, campos, linhas):
    with ficheiro.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-dias", type=int, default=150)
    ap.add_argument("--minutos", type=float, default=90, help="pára e guarda ao fim deste tempo")
    ap.add_argument("--vader", action="store_true", help="usar VADER se o RoBERTa falhar (só testes)")
    args = ap.parse_args()
    arranque = time.monotonic()

    PASTA.mkdir(parents=True, exist_ok=True)
    f_dia, f_asp = PASTA / "diario.csv", PASTA / "aspetos.csv"
    diario = {l["data"]: l for l in ler(f_dia)}
    aspetos = [l for l in ler(f_asp)]

    ontem = datetime.now(timezone.utc).date() - timedelta(days=1)
    todos = [INICIO + timedelta(days=i) for i in range((ontem - INICIO).days + 1)]
    em_falta = [d for d in reversed(todos) if d.isoformat() not in diario][: args.max_dias]
    print(f"Sentimento: {len(em_falta)} dias para tratar nesta execução "
          f"({len(diario)} já feitos de {len(todos)}).")
    if not em_falta:
        return

    modelo = Classificador(permitir_vader=args.vader)
    print(f"   Modelo: {modelo.nome}")
    feitos = 0
    for dia in em_falta:
        if (time.monotonic() - arranque) / 60 > args.minutos:
            print(f"   Tempo esgotado ({args.minutos:.0f} min); o resto fica para a próxima execução.")
            break
        textos = amostra_do_dia(dia)
        if textos is None:
            print(f"   {dia}: o arquivo não respondeu; fica para a próxima.")
            continue
        rotulos = modelo(textos)
        conta = Counter(rotulos)
        d = dia.isoformat()
        diario[d] = {"data": d, "n": len(textos), "positivo": conta["positive"], "neutro": conta["neutral"],
                     "negativo": conta["negative"], "modelo": modelo.nome}
        aspetos = [l for l in aspetos if l["data"] != d]
        for aspeto, rx in REGEX.items():
            sel = [r for t, r in zip(textos, rotulos) if rx.search(t)]
            if sel:
                c = Counter(sel)
                aspetos.append({"data": d, "aspeto": aspeto, "n": len(sel), "positivo": c["positive"],
                                "neutro": c["neutral"], "negativo": c["negative"]})
        feitos += 1
        if feitos % 10 == 0:  # vai guardando, para não perder trabalho se o tempo acabar
            escrever(f_dia, ["data", "n", "positivo", "neutro", "negativo", "modelo"],
                     [diario[k] for k in sorted(diario)])
            escrever(f_asp, ["data", "aspeto", "n", "positivo", "neutro", "negativo"],
                     sorted(aspetos, key=lambda l: (l["data"], l["aspeto"])))
            print(f"   {feitos}/{len(em_falta)} dias tratados (último: {d}, {len(textos)} comentários)")

    escrever(f_dia, ["data", "n", "positivo", "neutro", "negativo", "modelo"], [diario[k] for k in sorted(diario)])
    escrever(f_asp, ["data", "aspeto", "n", "positivo", "neutro", "negativo"],
             sorted(aspetos, key=lambda l: (l["data"], l["aspeto"])))
    print(f"   Feito: {feitos} dias novos. Total: {len(diario)} de {len(todos)} dias.")


if __name__ == "__main__":
    sys.exit(main())
