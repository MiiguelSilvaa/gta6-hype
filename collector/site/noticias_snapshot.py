# Snapshot do Google News (pesquisa "GTA 6" OR "GTA VI", últimas 48 h), recolhido a 11 out 2026 00:15 (Lisboa).
# 100 resultados; o artigo da CBS News aparece duplicado (http/https) e conta uma vez -> 99 artigos.
# Classificação das fontes feita à mão (v0.1).

RECOLHIDO = "2026-10-11T00:15:00+01:00"

FONTES = [
    "The Express Tribune", "GTA BOOM", "Neowin", "eTeknix", "Rock Paper Shotgun", "Eurogamer.net",
    "MMORPG.com", "iXBT.games", "TechRadar", "VideoCardz.com", "Gagadget.com", "iXBT.games", "MP1st",
    "BGR", "eTeknix", "Moneycontrol.com", "Notebookcheck", "Instinct Magazine", "Kotaku", "OpenCritic",
    "Wide Open Country", "Martin Cid Magazine", "IGN", "Insider Gaming", "DualShockers", "PlayDayOne",
    "Mashable", "Indy100", "Forbes", "Polygon.com", "OpenCritic", "eTeknix", "DancehallMag", "Mashable",
    "DancehallMag", "YouTube", "GamesRadar+", "Collider", "Pasquale Pillitteri", "Video Games Chronicle",
    "LevelUp", "eTeknix", "Mashable", "Notebookcheck", "GAMINGbible", "virus.hr", "Official Charts",
    "Notebookcheck", "GTA BOOM", "The Coast News", "GAMINGbible", "OpenCritic", "Absolute Geeks",
    "OpenCritic", "GAMINGbible", "tech-insider.org", "IMDb", "IGN", "Polygon.com", "Northeast Times",
    "Yahoo Finance", "Gadget Flow", "Gamereactor UK", "Kotaku", "Security Clearance Jobs", "103 WEUP",
    "Martin Cid Magazine", "Polygon.com", "Nintendo Everything", "New Game Network", "DualShockers",
    "VICE", "Yahoo Tech", "Nintendo Life", "Polygon.com", "Top Gear", "Billboard", "IGN", "IGN",
    "Yahoo Tech", "CBS News", "Variety", "DJ Mag", "GameSpot", "Men's Journal", "VICE", "PC Guide",
    "tech-insider.org", "GAMINGbible", "DLCompare.com", "Stocktwits", "Notebookcheck", "Rockstar Games",
    "BBC", "shattered.io", "tech-insider.org", "IGN Africa", "Digital Music News", "Man of Many",
]

CULTURA = {
    "Instinct Magazine", "Wide Open Country", "Martin Cid Magazine", "DancehallMag", "Collider",
    "Official Charts", "IMDb", "103 WEUP", "VICE", "Top Gear", "Billboard", "Variety", "DJ Mag",
    "Men's Journal", "Digital Music News", "Man of Many",
}
GERAL = {
    "The Express Tribune", "Moneycontrol.com", "Indy100", "Forbes", "The Coast News", "Northeast Times",
    "Yahoo Finance", "Security Clearance Jobs", "CBS News", "Stocktwits", "BBC",
}

# Manchetes escolhidas (sem conteúdo explícito dos leaks). Hora em UTC.
ULTIMAS = [
    ("Nintendo leaves GTA 6 Switch 2 possibility up to Rockstar Games", "The Express Tribune", "2026-10-10T22:08:33Z"),
    ("GTA 6 Hacker Arion Kurtaj Heads to Trial Days Before November 19 Launch", "GTA BOOM", "2026-10-10T21:18:12Z"),
    ("GTA 6 leaker threatens to drop fully playable build if crypto goal is achieved", "Neowin", "2026-10-10T20:40:00Z"),
    ("Rockstar Games Is Reportedly Sending Free GTA 6 Posters to Fans Who Email the Company", "eTeknix", "2026-10-10T20:39:56Z"),
    ("GTA 6 Previews Some Of Its Radio Stations, Including Slayer As The Metal Station's DJ", "MMORPG.com", "2026-10-10T19:30:00Z"),
    ("13 years on and with GTA 6 around the corner, GTA 5 is still a masterpiece", "TechRadar", "2026-10-10T19:00:00Z"),
]
FORA_DO_GAMING = [
    ("Cardi B Makes a Splash on ‘GTA VI: The Album’ Soundtrack With Cocky ‘Don’t Chart’", "Billboard", "2026-10-09T15:59:41Z"),
    ("GTA VI confirms Bad Bunny, Burna Boy and Lana Del Rey", "BBC", "2026-10-09T09:01:43Z"),
    ("GTA VI radio station features Miami’s own Trina and Trick Daddy", "CBS News", "2026-10-09T14:06:00Z"),
    ("From Travis Scott to Fred Again: Every artist set to feature on GTA VI", "Official Charts", "2026-10-10T09:15:58Z"),
    ("‘GTA 6’ Leaker To Release The Entire Game Build If Rockstar Doesn’t Meet Demands", "Forbes", "2026-10-10T15:02:16Z"),
    ("Video game console sales are plummeting. Can GTA VI turn things around?", "Yahoo Finance", "2026-10-09T20:53:08Z"),
]
