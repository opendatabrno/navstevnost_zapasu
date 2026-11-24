"""Odhadne návštěvu a původ fanoušků z exportů Intiq.

Vstup:   data/raw/intiq/*.csv, data/raw/ruian/*.geojson, data/zapasy.csv
Výstup:  data/processed/zapasy_odhad.csv, puvod_<uroven>.csv, zapasy_okresy.csv,
         zapasy_vzdalenost.csv, profil_prijezdu.csv
         (negitováno – výsledky nezveřejňovat, dokud není jasná licence)
Použití: python scripts/zpracuj_intiq.py

Návštěva: přítomní návštěvníci minus baseline ze dnů bez zápasu.
Původ:    přijíždějící rezidenti (jedou přímo z hexagonu, kde bydlí) minus baseline.
"""

from pathlib import Path

import geopandas as gpd
import h3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
VYSTUP = ROOT / "data" / "processed"

# Před tímto okamžikem mají Přijíždějící místní čas chybně označený jako UTC.
HRANICE_POSUNU = pd.Timestamp("2025-03-01")
OKNO_DNU = 35  # baseline jen ze dnů blízkých zápasu (úroveň dat se v čase mění)
PRITOMNI = (-180, 285)  # minuty od buly, první a poslední interval
PRIJEZDY = (-180, 30)
NAVSTEVNICI = ["RegularVisitors", "IrregularVisitors"]
HALA = "891e0695123ffff"
PASMA_KM = [0, 1, 3, 8, 20, 50, 100, 1000]
REZIDENTI = ["RegularResidents", "IrregularResidents"]
SVATKY = {
    "2024-01-01", "2024-03-29", "2024-04-01", "2024-09-28", "2024-10-28", "2024-12-24",
    "2024-12-25", "2024-12-26", "2025-01-01", "2025-04-18", "2025-04-21", "2025-09-28",
    "2025-10-28", "2025-11-17", "2025-12-24", "2025-12-25", "2025-12-26", "2026-01-01",
    "2026-09-28", "2026-10-28",
}


def mistni(cas: pd.Series) -> pd.Series:
    return cas.dt.tz_convert("Europe/Prague").dt.tz_localize(None)


def nacti(vzor: str) -> pd.DataFrame:
    soubory = sorted((RAW / "intiq").glob(vzor))
    if not soubory:
        raise SystemExit(f"chybí {RAW / 'intiq' / vzor}")
    return pd.concat([pd.read_csv(s) for s in soubory], ignore_index=True).drop_duplicates()


def nacti_pritomne() -> pd.Series:
    d = nacti("PresentPopulation_*.csv")
    d["cas"] = mistni(pd.to_datetime(d["DateFrom"], utc=True))
    # v noci změny na zimní čas se místní hodina opakuje
    return d.drop_duplicates("cas").set_index("cas")["Visitors"].sort_index()


def nacti_prijezdy() -> pd.DataFrame:
    d = nacti("CatchmentAreaRelations_*.csv")
    utc = pd.to_datetime(d["DateFrom"], utc=True)
    znacka = utc.dt.tz_localize(None)
    d["cas"] = znacka.where(znacka < HRANICE_POSUNU, mistni(utc))
    d["rezidenti"] = d[REZIDENTI].sum(axis=1)
    d["celkem"] = d["rezidenti"] + d[NAVSTEVNICI].sum(axis=1)
    return d[["SourceHexagonId", "cas", "rezidenti", "celkem"]].copy()


def vzdalenost(hexagon: str) -> float:
    return h3.great_circle_distance(h3.cell_to_latlng(hexagon), h3.cell_to_latlng(HALA))


def volny(den: pd.Timestamp) -> bool:
    return den.day_of_week >= 5 or f"{den:%Y-%m-%d}" in SVATKY


def uzemi(hexagony: list[str]) -> pd.DataFrame:
    """Přiřadí hexagonům (podle středu) obec, ORP, okres, kraj a městskou část Brna."""
    ll = [h3.cell_to_latlng(x) for x in hexagony]
    body = gpd.GeoDataFrame(
        {"hex": hexagony},
        geometry=gpd.points_from_xy([b for _, b in ll], [a for a, _ in ll]),
        crs=4326)
    vysl = pd.DataFrame(index=pd.Index(hexagony, name="hex"))
    for nazev in ("obce", "orp", "okresy", "kraje", "brno_casti"):
        hranice = gpd.read_file(RAW / "ruian" / f"{nazev}.geojson")[["kod", "nazev", "geometry"]]
        s = gpd.sjoin(body, hranice, how="left", predicate="within")
        s = s.drop_duplicates("hex").set_index("hex")
        vysl[nazev] = s["nazev"]
        vysl[f"{nazev}_kod"] = s["kod"]
    # Praha není v RÚIAN okresem ani nemá ORP ve stejném smyslu
    for nazev in ("okresy", "orp"):
        praha = vysl[nazev].isna() & (vysl["obce"] == "Praha")
        vysl.loc[praha, nazev] = "Praha"
        vysl.loc[praha, f"{nazev}_kod"] = 0
    return vysl


def main() -> None:
    v = nacti_pritomne()
    p = nacti_prijezdy()
    z = pd.read_csv(ROOT / "data" / "zapasy.csv")
    z["buly"] = pd.to_datetime(z["datum"] + " " + z["zacatek"])
    dny_dat = {f"{d:%Y-%m-%d}" for d in v.index.normalize().unique()}
    zapasy = z[z["datum"].isin(dny_dat)]
    print(f"zápasů s daty: {len(zapasy)} z {len(z)}")
    klidne = [pd.Timestamp(d) for d in sorted(dny_dat - set(z["datum"]))]

    p["den"] = p["cas"].dt.normalize()
    p["min"] = (p["cas"] - p["den"]).dt.total_seconds() / 60
    po_dnech = dict(tuple(p.groupby("den")))
    prazdne = p.iloc[:0]

    def okno(den: pd.Timestamp, buly: pd.Timestamp, sloupec: str) -> pd.Series:
        """Příjezdy podle hexagonu v okně kolem času buly, ale ve dni `den`."""
        zac = (buly - buly.normalize()).total_seconds() / 60
        d = po_dnech.get(den, prazdne)
        d = d[(d["min"] >= zac + PRIJEZDY[0]) & (d["min"] <= zac + PRIJEZDY[1])]
        return d.groupby("SourceHexagonId")[sloupec].sum()

    po_case = p.groupby("cas")[["rezidenti", "celkem"]].sum().to_dict()
    radky, puvod, profil = [], [], []
    for _, q in zapasy.iterrows():
        den, buly = pd.Timestamp(q["datum"]), q["buly"]
        zaklad = [d for d in klidne
                  if volny(d) == volny(den) and abs((d - den).days) <= OKNO_DNU]
        idx = pd.date_range(buly + pd.Timedelta(minutes=PRITOMNI[0]),
                            buly + pd.Timedelta(minutes=PRITOMNI[1]), freq="15min")
        bl = [np.nanmedian([v.get(d + (t - den), np.nan) for d in zaklad]) for t in idx]
        navic = pd.Series(v.reindex(idx).to_numpy() - np.array(bl), idx)
        rozdily = {}
        for sl in ("rezidenti", "celkem"):
            zakl = pd.concat([okno(d, buly, sl) for d in zaklad])
            zakl = zakl.groupby(level=0).sum() / len(zaklad)
            rozdily[sl] = okno(den, buly, sl).sub(zakl, fill_value=0)
        rozdil = rozdily["rezidenti"]
        celkem = okno(den, buly, "celkem").sum()
        celkem_bl = np.median([okno(d, buly, "celkem").sum() for d in zaklad])
        radky.append({
            "datum": q["datum"], "souper": q["souper"], "faze": q["faze"],
            "sezona": q["sezona"], "navstevnost_oficialni": q["navstevnost_oficialni"],
            "pritomni_navic": round(navic.max()),
            "prijezdy_navic": round(celkem - celkem_bl),
            "rezidenti_navic": round(rozdil.sum()), "dnu_baseline": len(zaklad),
        })
        puvod.append(pd.DataFrame({"navic": rozdily["rezidenti"], "navic_vse": rozdily["celkem"]})
                     .fillna(0).rename_axis("hex").reset_index().assign(datum=q["datum"]))
        for posun in range(PRIJEZDY[0], 105, 15):
            cas = buly + pd.Timedelta(minutes=posun)
            profil.append({"datum": q["datum"], "minut_od_buly": posun,
                           "rezidenti": po_case["rezidenti"].get(cas, 0),
                           "navstevnici": po_case["celkem"].get(cas, 0)
                           - po_case["rezidenti"].get(cas, 0)})

    VYSTUP.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(radky).to_csv(VYSTUP / "zapasy_odhad.csv", index=False, lineterminator="\n")
    pd.DataFrame(profil).to_csv(VYSTUP / "profil_prijezdu.csv", index=False, lineterminator="\n")
    puvod = pd.concat(puvod, ignore_index=True)
    puvod = puvod.join(uzemi(sorted(puvod["hex"].unique())), on="hex")
    puvod["pasmo_km"] = pd.cut(puvod["hex"].map(
        {x: vzdalenost(x) for x in puvod["hex"].unique()}), PASMA_KM, include_lowest=True)
    for soubor, sl in (("zapasy_okresy", ["kraje", "okresy"]), ("zapasy_vzdalenost", ["pasmo_km"])):
        g = puvod.groupby(["datum", *sl], observed=True)[["navic", "navic_vse"]].sum()
        g.reset_index().round(3).to_csv(VYSTUP / f"{soubor}.csv", index=False, lineterminator="\n")
    celkem = puvod["navic"].sum()
    na_zapas = puvod.groupby("datum")["navic"].sum()
    mimo = puvod.loc[puvod["obce"].isna(), "navic"].sum()
    print(f"rezidentů navíc: {celkem:.0f}, z toho mimo hranice ČR: {mimo:.0f}")
    for uroven in ("kraje", "okresy", "orp", "obce", "brno_casti"):
        d = puvod.dropna(subset=[uroven])
        m = d.groupby([f"{uroven}_kod", uroven, "datum"])["navic"].sum().unstack(fill_value=0)
        m = m.reindex(columns=zapasy["datum"], fill_value=0)
        t = pd.DataFrame({"navic_celkem": m.sum(axis=1)})
        # rozptyl mezi zápasy zahrnuje šum i skutečné rozdíly mezi zápasy
        t["smer_chyba"] = m.std(axis=1, ddof=1) * np.sqrt(m.shape[1])
        t["podil"] = t["navic_celkem"] / celkem
        # každý zápas má stejnou váhu (úroveň dat se mezi obdobími mění)
        t["podil_prumer"] = (m / na_zapas.reindex(m.columns)).mean(axis=1)
        t["zapasu_kladne"] = (m > 0).sum(axis=1)
        t["spolehlive"] = t["navic_celkem"] > 3 * t["smer_chyba"]
        t = t.sort_values("navic_celkem", ascending=False).reset_index()
        t = t.rename(columns={f"{uroven}_kod": "kod", uroven: "nazev"})
        t["kod"] = t["kod"].astype(int)
        t.round(4).to_csv(VYSTUP / f"puvod_{uroven}.csv", index=False, lineterminator="\n")
        sp = t[t["spolehlive"]]
        print(f"{uroven}: {len(t)} území, spolehlivých {len(sp)} (podíl {sp['podil'].sum():.0%})")


if __name__ == "__main__":
    main()
