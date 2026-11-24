"""Stáhne hranice obcí, ORP, okresů, krajů a brněnských městských částí z RÚIAN (ČÚZK).

Použití:  python scripts/stahni_hranice.py
Ukládá do data/raw/ruian/*.geojson (negitováno). Už stažené vrstvy přeskakuje.
Zdroj: ČÚZK, RÚIAN (https://ags.cuzk.gov.cz).
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CIL = ROOT / "data" / "raw" / "ruian"
BASE = "https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/MapServer"
BRNO = 582786  # kód obce Brno
ZJEDNODUSENI = 0.0002  # stupně, cca 20 m; hexagony jsou mnohem větší
STRANKA = 500

# název souboru: (číslo vrstvy, podmínka, sloupce)
VRSTVY = {
    "obce": (12, "1=1", "kod,nazev"),
    "orp": (14, "1=1", "kod,nazev"),
    "okresy": (15, "1=1", "kod,nazev"),
    "kraje": (17, "1=1", "kod,nazev"),
    "brno_casti": (8, f"obec={BRNO}", "kod,nazev"),
}


def dotaz(vrstva: int, **parametry) -> dict:
    url = f"{BASE}/{vrstva}/query?" + urllib.parse.urlencode(parametry)
    with urllib.request.urlopen(url, timeout=180) as r:
        data = json.load(r)
    if "error" in data:
        raise RuntimeError(f"{url}: {data['error']}")
    return data


def stahni(nazev: str) -> None:
    cesta = CIL / f"{nazev}.geojson"
    if cesta.exists():
        print(f"{nazev}: už staženo")
        return
    vrstva, kde, sloupce = VRSTVY[nazev]
    pocet = dotaz(vrstva, where=kde, returnCountOnly="true", f="json")["count"]
    prvky = []
    while len(prvky) < pocet:
        davka = dotaz(
            vrstva, where=kde, outFields=sloupce, outSR=4326, f="geojson",
            orderByFields="kod", resultOffset=len(prvky), resultRecordCount=STRANKA,
            maxAllowableOffset=ZJEDNODUSENI, geometryPrecision=5,
        )["features"]
        if not davka:
            break
        prvky += davka
    kody = {p["properties"]["kod"] for p in prvky}
    if len(prvky) != pocet or len(kody) != pocet:
        raise RuntimeError(f"{nazev}: {len(prvky)} prvků, {len(kody)} kódů, čekáno {pocet}")
    CIL.mkdir(parents=True, exist_ok=True)
    cesta.write_text(
        json.dumps({"type": "FeatureCollection", "features": prvky}, ensure_ascii=False),
        encoding="utf-8")
    print(f"{nazev}: {pocet} prvků -> {cesta}")


if __name__ == "__main__":
    for n in VRSTVY:
        stahni(n)
