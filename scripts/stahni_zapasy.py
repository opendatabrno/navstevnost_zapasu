"""Stáhne odehrané domácí zápasy HC Kometa Brno z hokej.cz do data/zapasy.csv.

Zápasy Ligy mistrů (hokej.cz je nevede) se připojí z data/zapasy_liga_mistru.csv.

Použití:  python scripts/stahni_zapasy.py
Stránky se ukládají do data/raw/hokej_cz/ (negitováno), opakované spuštění
je už nestahuje (kromě seznamu zápasů poslední sezóny).
"""

import csv
import html
import re
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "raw" / "hokej_cz"
VYSTUP = ROOT / "data" / "zapasy.csv"
LIGA_MISTRU = ROOT / "data" / "zapasy_liga_mistru.csv"

BASE = "https://www.hokej.cz"
TYM_ID = 22  # HC Kometa Brno
SEZONY = range(2023, 2027)  # rok začátku sezóny: 2023/24 až 2026/27
OD = "2024-01-01"  # starší data Intiq nemá
STADION = "Winning Group Arena"  # zajímají nás jen zápasy v této hale
PAUZA_S = 1.0

SLOUPCE = [
    "datum", "zacatek", "sezona", "faze", "kolo", "souper", "souper_plny_nazev",
    "skore", "navstevnost_oficialni", "stadion", "zapas_id",
    "zdroj",
]


def stahni(url: str, soubor: str, obnovit: bool = False) -> str:
    cesta = CACHE / soubor
    if cesta.exists() and not obnovit:
        return cesta.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8")
    CACHE.mkdir(parents=True, exist_ok=True)
    cesta.write_text(text, encoding="utf-8")
    time.sleep(PAUZA_S)
    return text


def cisty(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def jeden(vzor: str, text: str, co: str) -> str:
    m = re.search(vzor, text, re.S)
    if not m:
        raise ValueError(f"nenalezeno: {co}")
    return cisty(m.group(1))


def domaci_zapasy(sezona: int) -> list[str]:
    url = (f"{BASE}/tipsport-extraliga/zapasy?matchList-filter-season={sezona}"
           f"&matchList-filter-competition=0&matchList-filter-team={TYM_ID}")
    text = stahni(url, f"seznam_{sezona}.html", obnovit=sezona == SEZONY[-1])
    ids = []
    for m in re.finditer(r'<tr data-href="/zapas/(\d+)".*?</tr>', text, re.S):
        domaci = re.search(r'preview__name--long">([^<]*)', m.group(0)).group(1)
        odehrano = len(re.findall(r'preview__score[^>]*>(?:<[^>]*>)*\s*\d+', m.group(0))) == 2
        if "Kometa" in domaci and odehrano:
            ids.append(m.group(1))
    return ids


def faze(soutez: str, kolo: str) -> str:
    s = soutez.lower()
    if "baráž" in s:
        return "baráž"
    if "play off" in s:
        return "předkolo" if kolo.lower().startswith("předkolo") else "play-off"
    if s == "tipsport extraliga":
        return "základní část"
    raise ValueError(f"neznámá soutěž: {soutez!r}")


def zapas(zapas_id: str, sezona: int) -> dict:
    text = stahni(f"{BASE}/zapas/{zapas_id}", f"zapas_{zapas_id}.html")
    m = re.search(r'<div class="container page match">(.*?)<div class="nav-tab">', text, re.S)
    if not m:
        raise ValueError("nenalezena hlavička zápasu")
    hlavicka = m.group(1)
    polozky = [cisty(x) for x in re.findall(r"<li>(.*?)</li>", hlavicka, re.S)]
    soutez, cas_text, kolo = polozky[:3]
    cas = datetime.strptime(cas_text, "%d.%m.%Y %H:%M")
    host = re.search(r'<div class="team-visiting">(.*)', hlavicka, re.S).group(1)
    skore = re.search(
        r'class="home">\s*(\d+).*?class="visiting">\s*(\d+)', hlavicka, re.S)
    divaci = re.search(r'box-count-visitors">\s*([\d\s]*)<', text)
    divaci = re.sub(r"\s", "", divaci.group(1)) if divaci else ""
    return {
        "datum": f"{cas:%Y-%m-%d}",
        "zacatek": f"{cas:%H:%M}",
        "sezona": f"{sezona}/{(sezona + 1) % 100:02d}",
        "faze": faze(soutez, kolo),
        "kolo": kolo,
        "souper": jeden(r'<h2 class="medium">(.*?)</h2>', host, "soupeř"),
        "souper_plny_nazev": jeden(r'<h2 class="long">(.*?)</h2>', host, "soupeř"),
        "skore": f"{skore.group(1)}:{skore.group(2)}" if skore else "",
        "navstevnost_oficialni": divaci,
        "stadion": jeden(r'box-heading-stadium[^>]*>([^<]*)', text, "stadion"),
        "zapas_id": zapas_id,
        "zdroj": f"{BASE}/zapas/{zapas_id}",
    }


def main() -> None:
    radky = []
    for sezona in SEZONY:
        for zapas_id in domaci_zapasy(sezona):
            try:
                radky.append(zapas(zapas_id, sezona))
            except Exception as e:
                raise SystemExit(f"{BASE}/zapas/{zapas_id}: {e}") from e
    for r in radky:
        if r["datum"] >= date.today().isoformat():  # dnešní zápas může být rozehraný
            (CACHE / f"zapas_{r['zapas_id']}.html").unlink(missing_ok=True)
    radky = [r for r in radky if OD <= r["datum"] < date.today().isoformat()]
    with LIGA_MISTRU.open(encoding="utf-8", newline="") as f:
        radky += csv.DictReader(f)
    jinde = [r for r in radky if STADION not in r["stadion"]]
    for r in jinde:
        print(f"vynecháno (jiná hala): {r['datum']} {r['souper']} – {r['stadion']}")
    radky = [r for r in radky if r not in jinde]
    radky.sort(key=lambda r: (r["datum"], r["zacatek"]))
    with VYSTUP.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, SLOUPCE, lineterminator="\n")
        w.writeheader()
        w.writerows(radky)
    print(f"{len(radky)} zápasů -> {VYSTUP}")


if __name__ == "__main__":
    main()
