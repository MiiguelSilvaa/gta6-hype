"""
Gera docs/dados.js, o ficheiro que o site lê, a partir do que está em data/.
Corre no fim da recolha diária (diario.py). Também podes correr à mão com o ▶.
"""
import csv
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DADOS = RAIZ / "data"
SAIDA = RAIZ / "docs" / "dados.js"
FONTES = Path(__file__).resolve().parent / "fontes.json"

PAISES = {"United States": "US", "United Kingdom": "UK", "Portugal": "PT", "Brazil": "BR"}
LANCAMENTO = date(2026, 11, 19)

# Acontecimentos confirmados em notícias da altura: data -> (rótulo curto, descrição)
EVENTOS = {
    "2023-11-08": ("Anúncio do trailer", "Rockstar confirma o 1.º trailer para dezembro"),
    "2023-12-01": ("Data do 1.º trailer", "Rockstar anuncia que o 1.º trailer sai a 5 de dezembro"),
    "2023-12-05": ("1.º trailer", "Sai o 1.º trailer do GTA VI"),
    "2023-12-21": ("Sentença do hacker", "Hacker do leak de 2022 recebe sentença no Reino Unido"),
    "2024-05-16": ("Data: outono 2025", "Take-Two aponta o lançamento para o outono de 2025"),
    "2025-05-02": ("Adiado p/ maio 2026", "Primeiro adiamento: 26 de maio de 2026"),
    "2025-05-06": ("2.º trailer", "Sai o 2.º trailer"),
    "2025-11-07": ("Adiado p/ 19 nov", "Segundo adiamento: 19 de novembro de 2026"),
    "2026-06-18": ("Data das pré-reservas", "Rockstar anuncia que as pré-reservas abrem a 25 de junho"),
    "2026-06-24": ("Preço revelado", "Preço revelado (79,99 $) na véspera das pré-reservas"),
    "2026-08-06": ("Anúncio na Netflix", "Rockstar anuncia “An Extended Look”, com estreia na Netflix"),
    "2026-08-20": ("Leaks do Cyberleek", "O grupo Cyberleek começa a divulgar vídeos do jogo"),
    "2026-08-27": ("An Extended Look", "Estreia de “GTA VI: An Extended Look”, com a Netflix"),
    "2026-10-07": ("Novo leak + rádios", "Semana do novo leak de 25 minutos e do anúncio das rádios"),
    "2026-10-15": ("Trailer de lançamento", "Rockstar lança o trailer de lançamento, com banda sonora dos Justice"),
}

PALAVRAS_GAMING = ("game", "gaming", "gamer", "nintendo", "xbox", "playstation", "ps5", "ign", "kotaku",
                   "polygon", "eurogamer", "esports", "dexerto", "gta", "rockstar", "steam", "console", "tech")
PALAVRAS_EVITAR = ("nude", "naked", "nudity", "nsfw", "porn", "sex", "dong")  # manchetes que não mostramos


def carregar_fontes():
    dados = json.loads(FONTES.read_text(encoding="utf-8"))
    return {k: set(v) for k, v in dados.items() if not k.startswith("_")}


def classificar(fonte, url, fontes):
    for categoria in ("cultura", "geral", "gaming"):
        if fonte in fontes.get(categoria, ()):
            return categoria
    texto = f"{fonte} {url or ''}".lower()
    if any(p in texto for p in PALAVRAS_GAMING):
        return "gaming"
    return "outros"


def detetar_picos(valores, inicio, minimo, maximo=14, recentes=60):
    """Dias com >= minimo e >= 2x a média dos 7 dias anteriores; um pico por acontecimento.
    Os maiores entram até 'maximo'; os dos últimos 'recentes' dias entram sempre."""
    candidatos = []
    for i, v in enumerate(valores):
        janela = [x for x in valores[max(0, i - 7):i] if x is not None]
        if v is None or len(janela) < 3:
            continue
        media = sum(janela) / len(janela)
        mult = v / max(media, 1)
        if v >= minimo and mult >= 2:
            candidatos.append((v, i, round(media, 1), round(mult, 1)))
    escolhidos = []
    for v, i, media, mult in sorted(candidatos, key=lambda c: (-c[0], c[1])):
        if all(abs(i - e["i"]) > 3 for e in escolhidos):
            escolhidos.append({"i": i, "n": v, "media7": media, "mult": mult})
        if len(escolhidos) == maximo:
            break
    limite_recente = len(valores) - recentes
    for v, i, media, mult in sorted(candidatos, key=lambda c: (-c[0], c[1])):
        if i >= limite_recente and all(abs(i - e["i"]) > 3 for e in escolhidos):
            escolhidos.append({"i": i, "n": v, "media7": media, "mult": mult})
    escolhidos.sort(key=lambda e: e["i"])
    for e in escolhidos:
        e["data"] = (inicio + timedelta(days=e.pop("i"))).isoformat()
    return escolhidos


# Temas para identificar picos novos pelas manchetes do Google News (o primeiro que encaixar ganha)
TEMAS_MANCHETES = [
    (r"launch trailer|final trailer", "Trailer de lançamento"),
    (r"\btrailer\b", "Novo trailer"),
    (r"\bdelay|postpone|pushed back", "Adiamento"),
    (r"\bleak", "Leaks"),
    (r"pre-?orders?|\bprice\b|\$\d", "Preço e pré-reservas"),
    (r"\breviews?\b|metacritic|opencritic", "Análises da imprensa"),
    (r"radio|soundtrack|\bsong|\balbum|\bmusic", "Música e rádios"),
    (r"gameplay", "Gameplay"),
    (r"\bpc\b|steam", "Versão PC"),
]


def rotulo_pelas_manchetes(dia):
    """Olha para as notícias publicadas no dia do pico e no seguinte e devolve (curto, longo) ou None."""
    pasta = DADOS / "noticias"
    artigos, vistos = [], set()
    for k in range(0, 3):
        ficheiro = pasta / f"{(dia + timedelta(days=k)).isoformat()}.json"
        if not ficheiro.exists():
            continue
        for a in json.loads(ficheiro.read_text(encoding="utf-8")).get("artigos", []):
            publicado = date.fromisoformat(a["d"][:10])
            if dia <= publicado <= dia + timedelta(days=1) and a["t"] not in vistos:
                vistos.add(a["t"])
                artigos.append(a)
    if len(artigos) < 5:
        return None
    for padrao, nome in TEMAS_MANCHETES:
        rx = re.compile(padrao, re.IGNORECASE)
        com_tema = [a for a in artigos if rx.search(a["t"]) and not any(p in a["t"].lower() for p in PALAVRAS_EVITAR)]
        if len(com_tema) >= max(5, len(artigos) // 4):
            primeira = min(com_tema, key=lambda a: a["d"])
            return nome, f"{nome}: “{primeira['t']}” ({primeira['s']}). Identificado pelas manchetes do dia."
    return None


def rotular(picos, tolerancia=0, manchetes=None):
    datas_eventos = {date.fromisoformat(d): v for d, v in EVENTOS.items()}
    for p in picos:
        dia = date.fromisoformat(p["data"])
        perto = sorted((abs((dia - d).days), d) for d in datas_eventos if abs((dia - d).days) <= tolerancia)
        automatico = rotulo_pelas_manchetes(dia) if not perto else None
        if perto:
            p["curto"], p["longo"] = datas_eventos[perto[0][1]]
        elif automatico:
            p["curto"], p["longo"] = automatico
            p["auto"] = True
        elif manchetes and manchetes.get(p["data"]):
            titulo, meio = manchetes[p["data"]]
            p["curto"], p["longo"] = None, f"Manchete do dia: “{titulo}” ({meio})"
        else:
            p["curto"], p["longo"] = None, None
    return picos


def ler_csv(caminho):
    with caminho.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def imprensa():
    """Media Cloud (recolha única, não diária)."""
    volume = DADOS / "mediacloud" / "volume_diario.csv"
    paises = {}
    if volume.exists():
        linhas = ler_csv(volume)
        datas = sorted({l["date"] for l in linhas})
        inicio, fim = date.fromisoformat(datas[0]), date.fromisoformat(datas[-1])
        n = (fim - inicio).days + 1
        for l in linhas:
            codigo = PAISES.get(l["pais"])
            if not codigo:
                continue
            p = paises.setdefault(codigo, {"diario": [0] * n, "total": 0, "colecao": 0})
            i = (date.fromisoformat(l["date"]) - inicio).days
            p["diario"][i] = int(float(l["count"]))
            p["total"] += int(float(l["count"]))
            p["colecao"] += int(float(l.get("total_count") or 0))
    else:
        guardado = json.loads((DADOS / "site" / "mediacloud_site.json").read_text(encoding="utf-8"))
        inicio, fim = date.fromisoformat(guardado["inicio"]), date.fromisoformat(guardado["fim"])
        for codigo, v in guardado["paises"].items():
            paises[codigo] = {"diario": v["diario"], "total": v["total"], "colecao": v["total_noticias_colecao"]}
    ordem = [c for c in ("US", "UK", "PT", "BR") if c in paises]
    paises = {c: paises[c] for c in ordem}
    n = len(next(iter(paises.values()))["diario"])
    total = [sum(p["diario"][i] for p in paises.values()) for i in range(n)]

    # Para picos sem descrição confirmada: uma manchete desse dia que fale mesmo do jogo
    manchetes = {}
    ficheiro = DADOS / "mediacloud" / "picos_manchetes.csv"
    if ficheiro.exists():
        candidatas = {}
        for l in ler_csv(ficheiro):
            titulo = (l.get("title") or "").strip()
            baixo = titulo.lower()
            if not ("gta" in baixo or "grand theft auto" in baixo) or any(p in baixo for p in PALAVRAS_EVITAR):
                continue
            prioridade = 0 if (l.get("language") or "") == "en" else 1
            atual = candidatas.get(l["date"])
            if atual is None or prioridade < atual[0]:
                candidatas[l["date"]] = (prioridade, titulo, l.get("media_name") or "")
        manchetes = {d: (t, m) for d, (_, t, m) in candidatas.items()}

    anos = Counter()
    for i, v in enumerate(total):
        anos[(inicio + timedelta(days=i)).year] += v
    return {
        "inicio": inicio.isoformat(), "fim": fim.isoformat(), "paises": paises,
        "picos": rotular(detetar_picos(total, inicio, minimo=10), tolerancia=1, manchetes=manchetes),
        "por_ano": {str(a): v for a, v in sorted(anos.items())}, "total": sum(total),
    }


def reddit():
    ficheiro = DADOS / "reddit" / "r_gta6_diario.csv"
    if not ficheiro.exists():
        return None
    hoje = datetime.now(timezone.utc).date()
    linhas = [l for l in ler_csv(ficheiro) if date.fromisoformat(l["data"]) < hoje]  # o dia de hoje ainda vai a meio
    if not linhas:
        return None
    inicio, fim = date.fromisoformat(linhas[0]["data"]), date.fromisoformat(linhas[-1]["data"])
    n = (fim - inicio).days + 1
    posts, comentarios = [0] * n, [None] * n
    for l in linhas:
        i = (date.fromisoformat(l["data"]) - inicio).days
        posts[i] = int(l["publicacoes"] or 0)
        comentarios[i] = int(l["comentarios"]) if l["comentarios"] else None
    return {
        "inicio": inicio.isoformat(), "fim": fim.isoformat(), "publicacoes": posts, "comentarios": comentarios,
        "picos": rotular(detetar_picos(posts, inicio, minimo=300, maximo=20), tolerancia=2),
        "total_publicacoes": sum(posts), "total_comentarios": sum(c for c in comentarios if c),
    }


def noticias():
    ultimo = DADOS / "noticias" / "ultimo.json"
    if not ultimo.exists():
        return None, []
    snap = json.loads(ultimo.read_text(encoding="utf-8"))
    fontes = carregar_fontes()
    artigos = sorted(snap["artigos"], key=lambda a: a["d"], reverse=True)
    for a in artigos:
        a["c"] = classificar(a["s"], a.get("u"), fontes)
    categorias = Counter(a["c"] for a in artigos)

    def mostravel(a):
        return not any(p in a["t"].lower() for p in PALAVRAS_EVITAR)

    def resumo(lista):
        return [{"t": a["t"], "s": a["s"], "d": a["d"], "c": a["c"]} for a in lista[:6]]

    exemplos = {}
    for c in ("cultura", "geral", "outros"):
        nomes = []
        for a in artigos:
            if a["c"] == c and a["s"] not in nomes:
                nomes.append(a["s"])
        exemplos[c] = nomes
    # Evolução diária, recalculada a partir das recolhas guardadas (usa sempre a classificação mais recente)
    composicao = []
    for ficheiro in sorted((DADOS / "noticias").glob("20*.json")):
        dia = json.loads(ficheiro.read_text(encoding="utf-8"))
        conta = Counter(classificar(a["s"], a.get("u"), fontes) for a in dia["artigos"])
        composicao.append({"data": ficheiro.stem, "total": len(dia["artigos"]),
                           **{c: conta.get(c, 0) for c in ("gaming", "cultura", "geral", "outros")}})
    return {
        "recolhido": snap["recolhido"], "total": len(artigos),
        "categorias": {c: categorias.get(c, 0) for c in ("gaming", "cultura", "geral", "outros")},
        "exemplos": exemplos,
        "ultimas": resumo([a for a in artigos if mostravel(a)]),
        "fora": resumo([a for a in artigos if a["c"] in ("cultura", "geral") and mostravel(a)]),
    }, composicao


def sentimento():
    """Hype vs Realidade: índice diário (% positivos - % negativos) e temas antes/depois do lançamento."""
    f_dia = DADOS / "sentimento" / "diario.csv"
    if not f_dia.exists():
        return None
    linhas = ler_csv(f_dia)
    if not linhas:
        return None
    modelo = Counter(l.get("modelo") or "" for l in linhas).most_common(1)[0][0]
    linhas = [l for l in linhas if (l.get("modelo") or "") == modelo]  # nunca misturar modelos
    por_dia = {l["data"]: l for l in linhas}
    inicio, fim = date.fromisoformat(min(por_dia)), date.fromisoformat(max(por_dia))
    n_dias = (fim - inicio).days + 1
    n, saldo = [], []
    for i in range(n_dias):
        l = por_dia.get((inicio + timedelta(days=i)).isoformat())
        if l and int(l["n"]):
            n.append(int(l["n"]))
            saldo.append(int(l["positivo"]) - int(l["negativo"]))
        else:
            n.append(0)
            saldo.append(0)

    datas_validas = set(por_dia)
    periodos = {"antes": Counter(), "depois": Counter(), "recente": Counter()}
    totais = {"antes": 0, "depois": 0, "recente": 0}
    recente_desde = fim - timedelta(days=29)
    for l in linhas:
        d = date.fromisoformat(l["data"])
        p = "antes" if d < LANCAMENTO else "depois"
        totais[p] += int(l["n"])
        if d >= recente_desde:
            totais["recente"] += int(l["n"])
    f_asp = DADOS / "sentimento" / "aspetos.csv"
    temas = {}
    for l in (ler_csv(f_asp) if f_asp.exists() else []):
        if l["data"] not in datas_validas:
            continue
        d = date.fromisoformat(l["data"])
        alvos = ["antes" if d < LANCAMENTO else "depois"] + (["recente"] if d >= recente_desde else [])
        for p in alvos:
            t = temas.setdefault(l["aspeto"], {k: Counter() for k in periodos})[p]
            for campo in ("n", "positivo", "neutro", "negativo"):
                t[campo] += int(l[campo])
    resumo_temas = {}
    for aspeto, por_periodo in temas.items():
        resumo_temas[aspeto] = {}
        for p, c in por_periodo.items():
            if c["n"]:
                resumo_temas[aspeto][p] = {
                    "n": c["n"], "indice": round(100 * (c["positivo"] - c["negativo"]) / c["n"], 1),
                    "quota": round(100 * c["n"] / max(totais[p], 1), 1)}
    return {
        "inicio": inicio.isoformat(), "fim": fim.isoformat(), "modelo": modelo,
        "n": n, "saldo": saldo, "dias_feitos": len(linhas),
        "dias_total": (fim - date(2023, 11, 1)).days + 1,
        "lancamento": LANCAMENTO.isoformat(), "totais": totais, "temas": resumo_temas,
        "eventos": [{"data": d, "curto": c} for d, (c, _) in sorted(EVENTOS.items())],
    }


def radar(imp, rd):
    """Junta os picos do Reddit (atualizados todos os dias) e da imprensa; picos a 2 dias ou menos são o mesmo."""
    entradas = []
    for origem, picos in (("reddit", (rd or {}).get("picos", [])), ("imprensa", imp["picos"])):
        for p in picos:
            dia = date.fromisoformat(p["data"])
            alvo = next((e for e in entradas if abs((e["_dia"] - dia).days) <= 2), None)
            if alvo is None:
                alvo = {"_dia": dia, "data": p["data"], "curto": None, "longo": None}
                entradas.append(alvo)
            alvo[origem] = {"n": p["n"], "mult": p["mult"]}
            if dia < alvo["_dia"]:
                alvo["_dia"], alvo["data"] = dia, p["data"]
            # descrição: confirmada > automática > manchete
            if p.get("curto") and not p.get("auto") and (not alvo["curto"] or alvo.get("auto")):
                alvo["curto"], alvo["longo"], alvo["auto"] = p["curto"], p["longo"], False
            elif p.get("curto") and not alvo["curto"]:
                alvo["curto"], alvo["longo"], alvo["auto"] = p["curto"], p["longo"], True
            elif p.get("longo") and not alvo["longo"]:
                alvo["longo"] = p["longo"]
    # Fica no radar: o que tem descrição, o que foi forte (3x ou mais) e tudo o que é recente
    fim = max((e["_dia"] for e in entradas), default=date.today())
    def forte(e):
        return max(e.get("reddit", {}).get("mult", 0), e.get("imprensa", {}).get("mult", 0)) >= 3
    entradas = [e for e in entradas if e["curto"] or forte(e) or (fim - e["_dia"]).days <= 60]
    for e in entradas:
        del e["_dia"]
    return sorted(entradas, key=lambda e: e["data"])


def main():
    dados = {"atualizado": datetime.now(timezone.utc).isoformat(timespec="minutes")}
    dados["mediacloud"] = imprensa()
    dados["reddit"] = reddit()
    dados["noticias"], dados["composicao"] = noticias()
    dados["sentimento"] = sentimento()
    dados["radar"] = radar(dados["mediacloud"], dados["reddit"])
    if dados["sentimento"]:
        dados["sentimento"]["eventos"] = [{"data": e["data"], "curto": e["curto"]} for e in dados["radar"] if e["curto"]]
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text("window.DADOS = " + json.dumps(dados, ensure_ascii=False, separators=(",", ":")) + ";\n",
                     encoding="utf-8")
    mc, rd, nw = dados["mediacloud"], dados["reddit"], dados["noticias"]
    print(f"     Imprensa: {mc['total']} notícias, {len(mc['picos'])} picos, países {list(mc['paises'])}")
    if rd:
        print(f"     Reddit: {rd['total_publicacoes']} publicações até {rd['fim']}, {len(rd['picos'])} picos")
    if nw:
        print(f"     Google News: {nw['total']} notícias {nw['categorias']}")
        if nw["exemplos"]["outros"]:
            print(f"     Sites por classificar (acrescentar em fontes.json): {nw['exemplos']['outros'][:15]}")
    st = dados["sentimento"]
    if st:
        print(f"     Sentimento: {st['dias_feitos']} dias ({st['inicio']} a {st['fim']}), modelo {st['modelo']}")
    print(f"     Escrito: {SAIDA}")


if __name__ == "__main__":
    main()
