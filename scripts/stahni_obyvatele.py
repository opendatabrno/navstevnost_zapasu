"""Sestaví data/obyvatele.csv: počet obyvatel obcí, okresů a městských částí Brna k 1. 1. 2026.

Obce a okresy: ČSÚ, datová sada OBY02A (CSV má asi 200 MB, zpracuje se průběžně).
Městské části Brna: MV ČR (občané + cizinci), přepočteno na součet Brna podle ČSÚ.

Použití:  python scripts/stahni_obyvatele.py   (potřebuje openpyxl)
"""

import csv
import io
import urllib.request
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
ROK = "2026"
BRNO = "582786"  # kód obce Brno
CSU = "https://data.csu.gov.cz/opendata/sady/OBY02A/distribuce/csv"
MV = "https://mv.gov.cz/documents/{}?disposition=attachment"
MV_OBCANE = MV.format("informativnipocetobcanucr-k01-01-2026")
MV_CIZINCI = MV.format("informativnipocetcizincuspobytem-k01-01-2026")


def otevri(url: str):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=300)


def csu() -> list[dict]:
    radky = []
    with otevri(CSU) as r:
        for q in csv.DictReader(io.TextIOWrapper(r, encoding="utf-8-sig", newline="")):
            if q["IndicatorType"] != "2406P" or q["POHL2"] != "0" or q["CasR"] != ROK:
                continue
            kod, nazev = q["UZ01234596C"], q["Všechna území"]
            # 6číselné kódy jsou obce, CZ + 4 znaky okresy (Praha je jen kraj CZ01)
            if kod.isdigit() and len(kod) == 6:
                uroven = "obce"
            elif kod == "CZ01" or (kod.startswith("CZ") and len(kod) == 6):
                uroven = "okresy"
            else:
                continue
            radky.append({"uroven": uroven, "kod": kod, "nazev": nazev, "obyvatel": int(q["Hodnota"])})
    return radky


def sesit(url: str):
    with otevri(url) as r:
        return openpyxl.load_workbook(io.BytesIO(r.read()), read_only=True, data_only=True)


def brnenske_casti(brno_celkem: int) -> list[dict]:
    casti = {}
    for r in sesit(MV_OBCANE)["Městské části"].iter_rows(values_only=True):
        if r[2] == "Brno" and isinstance(r[9], (int, float)) and str(r[4]).startswith("Brno"):
            casti[r[4]] = [int(r[3]), int(r[9])]
    for r in sesit(MV_CIZINCI).worksheets[0].iter_rows(values_only=True):
        if r[2] == "Brno" and r[3] in casti:
            casti[r[3]][1] += int(r[4])
    if len(casti) != 29:
        raise RuntimeError(f"městských částí {len(casti)}, čekáno 29")
    pomer = brno_celkem / sum(p for _, p in casti.values())
    print(f"MV -> ČSÚ: poměr {pomer:.3f}")
    return [{"uroven": "brno_casti", "kod": k, "nazev": n, "obyvatel": round(p * pomer)}
            for n, (k, p) in casti.items()]


def main() -> None:
    radky = csu()
    brno = next(r["obyvatel"] for r in radky if r["kod"] == BRNO)
    radky += brnenske_casti(brno)
    vystup = ROOT / "data" / "obyvatele.csv"
    with vystup.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["uroven", "kod", "nazev", "obyvatel"], lineterminator="\n")
        w.writeheader()
        w.writerows(radky)
    for u in ("obce", "okresy", "brno_casti"):
        x = [r["obyvatel"] for r in radky if r["uroven"] == u]
        print(f"{u}: {len(x)} území, {sum(x)} obyvatel")


if __name__ == "__main__":
    main()
