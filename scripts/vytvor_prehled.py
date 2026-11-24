"""Vytvoří z výsledků zpracuj_intiq.py přehled s mapou a grafy.

Výstup:  data/processed/prehled.html (negitováno – nezveřejňovat, dokud není jasná licence)
Použití: python scripts/vytvor_prehled.py
"""

import html
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"
RUIAN = ROOT / "data" / "raw" / "ruian"
HALA = (16.6053, 49.1856)  # přibližná poloha haly (lon, lat), jen značka v mapě
OKRUH_M = 65_000
PRAHY = [0.0005, 0.001, 0.0025, 0.005, 0.01]  # hranice tříd podílu v mapě
OKRES_SOUPERE = {
    "Sparta": "Praha", "Pardubice": "Pardubice", "Olomouc": "Olomouc", "Litvínov": "Most",
    "Vítkovice": "Ostrava-město", "Liberec": "Liberec", "Hr. Králové": "Hradec Králové",
    "Karlovy Vary": "Karlovy Vary", "Ml. Boleslav": "Mladá Boleslav", "Kladno": "Kladno",
    "Plzeň": "Plzeň-město", "Třinec": "Frýdek-Místek", "Č. Budějovice": "České Budějovice",
}
esc = html.escape


def cz(x: float, mist: int = 1) -> str:
    return f"{x:,.{mist}f}".replace(",", " ").replace(".", ",")


def pct(x: float, mist: int = 1) -> str:
    return cz(100 * x, mist) + " %"


def tabulka(hlava: list[str], radky: list[list[str]]) -> str:
    h = "".join(f"<th>{esc(x)}</th>" for x in hlava)
    r = "".join("<tr>" + "".join(f"<td>{esc(str(x))}</td>" for x in rad) + "</tr>" for rad in radky)
    return (f"<details><summary>Tabulka</summary><div class=tab><table><thead><tr>{h}</tr></thead>"
            f"<tbody>{r}</tbody></table></div></details>")


def karta(nadpis: str, popis: str, obsah: str, tab: str, cls: str = "") -> str:
    return (f'<section class="karta {cls}"><h2>{esc(nadpis)}</h2><p class=popis>{esc(popis)}</p>'
            f"{obsah}{tab}</section>")


def legenda(polozky: list[tuple[str, str]]) -> str:
    return "<div class=leg>" + "".join(
        f'<span><i style="background:{b}"></i>{esc(n)}</span>' for n, b in polozky) + "</div>"


def svg(w: int, h: int, obsah: str, popis: str) -> str:
    return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(popis)}">{obsah}</svg>'


def prumer_ci(x: pd.Series) -> tuple[float, float]:
    """Průměr a poloviční šířka 95% intervalu (normální aproximace)."""
    return x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan


# ---------- mapy ----------

def cesta(geom, fx, fy) -> str:
    casti = []
    for poly in getattr(geom, "geoms", [geom]):
        if poly.geom_type == "LineString":
            casti.append("M" + "L".join(f"{fx(x):.1f},{fy(y):.1f}" for x, y in poly.coords))
        if poly.geom_type != "Polygon":
            continue
        for kruh in (poly.exterior, *poly.interiors):
            casti.append("M" + "L".join(f"{fx(x):.1f},{fy(y):.1f}" for x, y in kruh.coords) + "Z")
    return "".join(casti)


def trida(x: float) -> int:
    return 1 + sum(x >= p for p in PRAHY)


def mapa(g: gpd.GeoDataFrame, w: int, obrysy: gpd.GeoDataFrame, popis: str) -> str:
    x0, y0, x1, y1 = g.total_bounds
    m = w / (x1 - x0)
    h = round((y1 - y0) * m)

    def fx(x):
        return (x - x0) * m

    def fy(y):
        return (y1 - y) * m

    o = []
    for r in g.itertuples():
        if r.spolehlive is True or r.spolehlive == 1:
            fill, stav = f"var(--q{trida(r.podil_prumer)})", pct(r.podil_prumer, 2)
        elif r.ma_data:
            fill, stav = "var(--nejiste)", f"{pct(r.podil_prumer, 2)} (nespolehlivé)"
        else:
            fill, stav = "var(--prazdne)", "bez příjezdů"
        o.append(f'<path d="{cesta(r.geometry, fx, fy)}" fill="{fill}" class=uz '
                 f'data-tip="{esc(r.nazev)}|{stav}"/>')
    for r in obrysy.itertuples():
        o.append(f'<path d="{cesta(r.geometry, fx, fy)}" class=obrys />')
    hala = gpd.GeoSeries(gpd.points_from_xy([HALA[0]], [HALA[1]]), crs=4326).to_crs(5514).iloc[0]
    o.append(f'<circle cx="{fx(hala.x):.1f}" cy="{fy(hala.y):.1f}" r="5" class=hala data-tip="Hala|"/>')
    return svg(w, h, "".join(o), popis)


def vrstva(nazev: str, zjednodusit: float) -> gpd.GeoDataFrame:
    g = gpd.read_file(RUIAN / f"{nazev}.geojson")[["kod", "nazev", "geometry"]].to_crs(5514)
    g["geometry"] = g.geometry.simplify(zjednodusit)
    return g


def s_podilem(g: gpd.GeoDataFrame, nazev: str) -> gpd.GeoDataFrame:
    d = pd.read_csv(DATA / f"puvod_{nazev}.csv")[["kod", "podil_prumer", "spolehlive"]]
    g = g.merge(d, on="kod", how="left")
    g["ma_data"] = g["podil_prumer"].notna()
    g["spolehlive"] = g["spolehlive"].eq(True)
    g["podil_prumer"] = g["podil_prumer"].fillna(0)
    return g


def legenda_mapy() -> str:
    b = [0, *PRAHY]
    pol = [(f"do {pct(b[1], 2)}", "var(--q1)")]
    pol += [(f"{pct(b[i], 2)} – {pct(b[i + 1], 2)}", f"var(--q{i + 1})") for i in range(1, 5)]
    pol += [(f"{pct(b[5], 0)} a víc", "var(--q6)"), ("nespolehlivé (šum)", "var(--nejiste)"),
            ("bez příjezdů", "var(--prazdne)")]
    return legenda(pol)


def karty_map() -> str:
    obce = vrstva("obce", 60)
    casti = vrstva("brno_casti", 30)
    hala = gpd.GeoSeries(gpd.points_from_xy([HALA[0]], [HALA[1]]), crs=4326).to_crs(5514).iloc[0]
    okoli = obce[(obce.distance(hala) < OKRUH_M) & (obce["nazev"] != "Brno")]
    g = pd.concat([s_podilem(okoli, "obce"), s_podilem(casti, "brno_casti")])
    okresy = vrstva("okresy", 100)
    # Praha je v RÚIAN krajem, ne okresem
    kraje = vrstva("kraje", 300)
    praha = kraje[kraje["nazev"].str.contains("Praha")].assign(kod=0, nazev="Praha")
    okr = s_podilem(pd.concat([vrstva("okresy", 300), praha]), "okresy")
    ramec = box(*g.total_bounds)
    obrys = okresy[okresy.intersects(ramec)].copy()
    obrys["geometry"] = obrys.geometry.make_valid().boundary.intersection(ramec)

    top = g[g["spolehlive"]].nlargest(25, "podil_prumer")
    t1 = tabulka(["Území", "Podíl rezidentů"], [[r.nazev, pct(r.podil_prumer, 2)] for r in top.itertuples()])
    topo = okr[okr["spolehlive"]].nlargest(20, "podil_prumer")
    t2 = tabulka(["Okres", "Podíl rezidentů"], [[r.nazev, pct(r.podil_prumer, 2)] for r in topo.itertuples()])
    leg = legenda_mapy()
    popis = ("Podíl na příjezdech lidí, kteří přijeli přímo z domova, po odečtení baseline. Průměr "
             "zápasů, každý má stejnou váhu. Větší území mají přirozeně víc lidí.")
    return (karta("Odkud fanoušci jezdí: Brno po městských částech a obce do 65 km", popis,
                  leg + mapa(g, 1000, obrys, "Mapa podílu podle obcí"), t1, "siroka")
            + karta("Odkud fanoušci jezdí: okresy Česka", popis,
                    leg + mapa(okr, 1000, okr.iloc[:0], "Mapa podílu podle okresů"), t2, "siroka"))


# ---------- grafy ----------

def osa_y(kroky: list[float], fy, x0: int, x1: int, fmt) -> str:
    return "".join(
        f'<line x1="{x0}" x2="{x1}" y1="{fy(k):.1f}" y2="{fy(k):.1f}" class=mriz />'
        f'<text x="{x0 - 8}" y="{fy(k) + 4:.1f}" class=osa text-anchor=end>{fmt(k)}</text>'
        for k in kroky)


def graf_vzdalenost() -> str:
    d = pd.read_csv(DATA / "zapasy_vzdalenost.csv")
    d["nav"] = d["navic_vse"] - d["navic"]
    poradi = list(dict.fromkeys(d.sort_values("pasmo_km", key=lambda s: s.str.extract(
        r"\(([-\d.]+),")[0].astype(float))["pasmo_km"]))
    nazvy = ["do 1 km", "1–3", "3–8", "8–20", "20–50", "50–100", "nad 100"]
    p = {}
    for sl in ("navic", "nav"):
        m = d.pivot(index="datum", columns="pasmo_km", values=sl).fillna(0)[poradi]
        p[sl] = m.div(m.sum(axis=1), axis=0).mean()
    w, h, x0, y0, y1 = 520, 300, 46, 20, 250
    mx = 0.4

    def fy(v):
        return y1 - v / mx * (y1 - y0)

    o = osa_y([0, .1, .2, .3, .4], fy, x0, w - 6, lambda k: pct(k, 0))
    krok = (w - 6 - x0) / len(poradi)
    radky = []
    for i, k in enumerate(poradi):
        for j, (sl, barva, jm) in enumerate((("navic", "--s1", "Rezidenti"), ("nav", "--s2", "Návštěvníci"))):
            v = max(p[sl][k], 0)
            x = x0 + i * krok + krok / 2 - 21 + j * 22
            t, b = fy(v), y1
            rr = min(4, b - t)
            o += (f'<path d="M{x:.1f},{b}V{t + rr:.1f}q0,-{rr:.1f} {rr:.1f},-{rr:.1f}h{20 - 2 * rr:.1f}'
                  f'q{rr:.1f},0 {rr:.1f},{rr:.1f}V{b}Z" fill="var({barva})" '
                  f'data-tip="{nazvy[i]} – {jm}|{pct(v)}"/>')
        o += f'<text x="{x0 + (i + .5) * krok:.1f}" y="{y1 + 18}" class=osa text-anchor=middle>{nazvy[i]}</text>'
        radky.append([nazvy[i], pct(p["navic"][k]), pct(p["nav"][k])])
    o += f'<text x="{(w + x0) / 2}" y="{y1 + 38}" class=osa text-anchor=middle>vzdálenost od haly (km)</text>'
    return karta("Jak daleko lidé na hokej jezdí",
                 "Podíl příjezdů podle vzdálenosti výchozího hexagonu. U návštěvníků jde o poslední "
                 "zastávku, ne o bydliště.",
                 legenda([("Rezidenti (z domova)", "var(--s1)"), ("Návštěvníci (odjinud)", "var(--s2)")])
                 + svg(w, h, o, "Sloupcový graf vzdáleností"),
                 tabulka(["Pásmo (km)", "Rezidenti", "Návštěvníci"], radky))


def graf_profil() -> str:
    d = pd.read_csv(DATA / "profil_prijezdu.csv")
    d["celkem"] = d["rezidenti"] + d["navstevnici"]
    m = d.pivot(index="datum", columns="minut_od_buly", values="celkem")
    pod = m.div(m.sum(axis=1), axis=0).mean()
    w, h, x0, y0, y1 = 520, 300, 46, 20, 250
    mx = max(0.2, np.ceil(pod.max() * 20) / 20)

    def fy(v):
        return y1 - v / mx * (y1 - y0)

    o = osa_y(list(np.arange(0, mx + .001, .05)), fy, x0, w - 6, lambda k: pct(k, 0))
    krok = (w - 6 - x0) / len(pod)
    for i, (k, v) in enumerate(pod.items()):
        t = fy(v)
        rr = min(4, y1 - t)
        x, s = x0 + i * krok + 1, krok - 2
        o += (f'<path d="M{x:.1f},{y1}V{t + rr:.1f}q0,-{rr:.1f} {rr:.1f},-{rr:.1f}h{s - 2 * rr:.1f}'
              f'q{rr:.1f},0 {rr:.1f},{rr:.1f}V{y1}Z" fill="var(--s1)" '
              f'data-tip="{k:+d} až {k + 15:+d} min od buly|{pct(v)} příjezdů v okně"/>')
        if k % 60 == 0:
            o += f'<text x="{x0 + i * krok:.1f}" y="{y1 + 18}" class=osa text-anchor=middle>{"buly" if k == 0 else f"{k // 60:+d} h"}</text>'
    xb = x0 + list(pod.index).index(0) * krok
    o += (f'<line x1="{xb:.1f}" x2="{xb:.1f}" y1="{y0}" y2="{y1}" class=ref />'
          f'<text x="{(w + x0) / 2}" y="{y1 + 38}" class=osa text-anchor=middle>čas od buly</text>')
    return karta("Kdy lidé přijíždějí",
                 "Rozložení příjezdů do hexagonu haly po 15 minutách, průměr zápasů. Baseline zde "
                 "není odečtená; síť telefon zaznamená typicky jednou za 30 minut.",
                 svg(w, h, o, "Sloupcový graf příjezdů v čase"),
                 tabulka(["Interval od buly (min)", "Podíl příjezdů"],
                         [[f"{k:+d} až {k + 15:+d}", pct(v)] for k, v in pod.items()]))


def graf_body(nadpis: str, popis: str, skupiny: list[tuple[str, pd.Series]], osa: str, sirka_stitku: int = 130) -> str:
    """Vodorovné tečky s 95% intervalem: (popisek, hodnoty po zápasech)."""
    st = [(n, len(x), *prumer_ci(x)) for n, x in skupiny]
    konec = max(a + (0 if np.isnan(c) else c) for _, _, a, c in st)
    krok_osy = 0.02 if konec <= 0.12 else 0.05 if konec <= 0.35 else 0.1
    mx = np.ceil(konec / krok_osy) * krok_osy
    rh, y0 = 26, 12
    w, x0 = 520, sirka_stitku
    h = y0 + rh * len(st) + 44

    def fx(v):
        return x0 + v / mx * (w - 20 - x0)

    dole = y0 + rh * len(st)
    o = "".join(
        f'<line x1="{fx(k):.1f}" x2="{fx(k):.1f}" y1="{y0}" y2="{dole}" class=mriz />'
        f'<text x="{fx(k):.1f}" y="{dole + 16}" class=osa text-anchor=middle>{pct(k, 0)}</text>'
        for k in np.arange(0, mx + krok_osy / 2, krok_osy))
    for i, (n, pocet, a, c) in enumerate(st):
        y = y0 + rh * (i + .5)
        rozsah = "" if np.isnan(c) else f" (95% interval {pct(max(a - c, 0))} – {pct(a + c)})"
        o += f'<text x="{x0 - 10}" y="{y + 4:.1f}" class=popisek text-anchor=end>{esc(n)} ({pocet})</text>'
        if not np.isnan(c):
            o += f'<line x1="{fx(max(a - c, 0)):.1f}" x2="{fx(a + c):.1f}" y1="{y:.1f}" y2="{y:.1f}" class=inter />'
        o += (f'<circle cx="{fx(a):.1f}" cy="{y:.1f}" r="5" class=bod fill="var(--s1)"/>'
              f'<rect x="{x0}" y="{y - rh / 2:.1f}" width="{w - x0}" height="{rh}" fill="transparent" '
              f'data-tip="{esc(n)}, zápasů: {pocet}|{pct(a)}{rozsah}"/>')
    o += f'<text x="{(w + x0) / 2}" y="{dole + 36}" class=osa text-anchor=middle>{esc(osa)}</text>'
    return karta(nadpis, popis, svg(w, h, o, nadpis),
                 tabulka(["Skupina", "Zápasů", "Průměr", "± 95 %"],
                         [[n, p, pct(a), "–" if np.isnan(c) else pct(c)] for n, p, a, c in st]))


def graf_soupere(z: pd.DataFrame, okr: pd.DataFrame) -> str:
    """Příjezdy z okresu soupeře na jeho zápas a na ostatní zápasy."""
    m = okr.pivot_table(index="datum", columns="okresy", values="navic_vse", aggfunc="sum").reindex(z["datum"]).fillna(0)
    radky = []
    for s, o in OKRES_SOUPERE.items():
        if o not in m:
            continue
        je = (z["souper"] == s).to_numpy()
        radky.append((s, o, int(je.sum()), m.loc[je, o].mean(), m.loc[~je, o].mean()))
    radky.sort(key=lambda r: -r[3])
    mx = max(5, np.ceil(max(max(r[3], r[4]) for r in radky) / 5) * 5)
    w, x0, y0, rh = 520, 200, 12, 26
    h = y0 + rh * len(radky) + 44
    dole = y0 + rh * len(radky)
    krok_osy = 5 if mx <= 40 else 10 if mx <= 80 else 20

    def fx(v):
        return x0 + max(v, 0) / mx * (w - 20 - x0)

    o = "".join(
        f'<line x1="{fx(k):.1f}" x2="{fx(k):.1f}" y1="{y0}" y2="{dole}" class=mriz />'
        f'<text x="{fx(k):.1f}" y="{dole + 16}" class=osa text-anchor=middle>{k:.0f}</text>'
        for k in np.arange(0, mx + 1, krok_osy))
    for i, (s, okres, n, a, b) in enumerate(radky):
        y = y0 + rh * (i + .5)
        o += (f'<text x="{x0 - 10}" y="{y + 4:.1f}" class=popisek text-anchor=end>{esc(s if s == okres else f"{s} – {okres}" if s in ("Sparta", "Litvínov", "Vítkovice", "Třinec") else s)} ({n})</text>'
              f'<line x1="{fx(b):.1f}" x2="{fx(a):.1f}" y1="{y:.1f}" y2="{y:.1f}" class=inter />'
              f'<circle cx="{fx(b):.1f}" cy="{y:.1f}" r="5" class=bod fill="var(--s2)"/>'
              f'<circle cx="{fx(a):.1f}" cy="{y:.1f}" r="5" class=bod fill="var(--s1)"/>'
              f'<rect x="{x0}" y="{y - rh / 2:.1f}" width="{w - x0}" height="{rh}" fill="transparent" '
              f'data-tip="{esc(s)} (okres {esc(okres)}, zápasů: {n})|na tento zápas {cz(a)}, na ostatní {cz(b)} lidí navíc"/>')
    o += f'<text x="{(w + x0) / 2}" y="{dole + 36}" class=osa text-anchor=middle>příjezdů navíc na zápas</text>'
    return karta("Přijíždějí hosté? Příjezdy z okresu soupeře",
                 "Lidé, jejichž poslední zastávka byla v okrese soupeře (rezidenti i návštěvníci). "
                 "Počty jsou malé a zatížené šumem; kdo se cestou zastavil, chybí.",
                 legenda([("zápas s tímto soupeřem", "var(--s1)"), ("ostatní zápasy", "var(--s2)")])
                 + svg(w, h, o, "Příjezdy z okresu soupeře"),
                 tabulka(["Soupeř", "Okres", "Zápasů", "Na jeho zápas", "Na ostatní"],
                         [[s, k, n, cz(a), cz(b)] for s, k, n, a, b in radky]))


def graf_navsteva(z: pd.DataFrame) -> str:
    skup = z["sezona"].map({"2023/24": 0, "2024/25": 1}).fillna(2).astype(int)
    jmena = ["2023/24 (od ledna)", "2024/25", "2025/26 a 2026/27"]
    barvy = ["var(--s1)", "var(--s2)", "var(--s3)"]
    w, h, x0, y0, y1 = 520, 340, 52, 14, 284
    mx = 8000

    def fx(v):
        return x0 + v / mx * (w - 16 - x0)

    def fy(v):
        return y1 - v / mx * (y1 - y0)

    o = osa_y([0, 2000, 4000, 6000, 8000], fy, x0, w - 16, lambda k: cz(k, 0))
    for k in (0, 2000, 4000, 6000, 8000):
        o += f'<text x="{fx(k):.1f}" y="{y1 + 18}" class=osa text-anchor=middle>{cz(k, 0)}</text>'
    o += (f'<line x1="{fx(0)}" y1="{fy(0)}" x2="{fx(mx)}" y2="{fy(mx)}" class=ref />'
          f'<text x="{fx(3000):.1f}" y="{fy(3000) - 10:.1f}" class=stitek text-anchor=end>odhad = oficiální</text>')
    for r, s in zip(z.itertuples(), skup):
        o += (f'<circle cx="{fx(r.navstevnost_oficialni):.1f}" cy="{fy(r.pritomni_navic):.1f}" r="5" class=bod '
              f'fill="{barvy[s]}" data-tip="{r.datum} {esc(r.souper)}|oficiálně {cz(r.navstevnost_oficialni, 0)}, '
              f'odhad {cz(r.pritomni_navic, 0)}"/>')
    o += f'<text x="{(w + x0) / 2}" y="{y1 + 38}" class=osa text-anchor=middle>oficiální návštěva</text>'
    return karta("Odhad z mobilní sítě a oficiální návštěva",
                 "Přítomní návštěvníci ve špičce zápasu minus baseline. Odhad je soustavně nižší a jeho "
                 "úroveň se mezi obdobími mění.",
                 legenda(list(zip(jmena, barvy))) + svg(w, h, o, "Bodový graf návštěvnosti"),
                 tabulka(["Datum", "Soupeř", "Oficiálně", "Odhad"],
                         [[r.datum, r.souper, cz(r.navstevnost_oficialni, 0), cz(r.pritomni_navic, 0)]
                          for r in z.itertuples()]))


def main() -> None:
    z = pd.read_csv(DATA / "zapasy_odhad.csv")
    kal = pd.read_csv(ROOT / "data" / "zapasy.csv")[["datum", "zacatek"]]
    z = z.merge(kal, on="datum")
    okr = pd.read_csv(DATA / "zapasy_okresy.csv")
    kraj = okr.pivot_table(index="datum", columns="kraje", values="navic", aggfunc="sum").reindex(z["datum"]).fillna(0)
    celkem = okr.groupby("datum")["navic"].sum().reindex(z["datum"])
    z["mimo_jmk"] = (1 - kraj["Jihomoravský kraj"] / celkem).to_numpy()
    brno = okr[okr["okresy"] == "Brno-město"].set_index("datum")["navic"].reindex(z["datum"])
    z["brno"] = (brno / celkem).to_numpy()
    den = pd.to_datetime(z["datum"]).dt.day_of_week
    liga = z["faze"].isin(["základní část", "play-off", "předkolo"])
    vikend = den >= 5

    def sk(maska, sl="mimo_jmk"):
        return z.loc[maska, sl]

    typy = [("Základní část", sk(z["faze"] == "základní část")),
            ("Play-off a předkolo", sk(z["faze"].isin(["play-off", "předkolo"]))),
            ("Liga mistrů", sk(z["faze"] == "Liga mistrů")),
            ("Víkend", sk(vikend)), ("Všední den", sk(~vikend))]
    sez = [(s, sk(z["sezona"] == s)) for s in sorted(z["sezona"].unique())]
    sezb = [(s, sk(z["sezona"] == s, "brno")) for s in sorted(z["sezona"].unique())]
    soup = sorted(((s, sk((z["souper"] == s) & liga)) for s in z.loc[liga, "souper"].unique()),
                  key=lambda t: -t[1].mean())

    dlazdice = "".join(
        f"<div class=dl><span>{esc(a)}</span><b>{esc(b)}</b></div>" for a, b in (
            ("Zápasů s daty", f"{len(z)} z {len(pd.read_csv(ROOT / 'data' / 'zapasy.csv'))}"),
            ("Z Brna", pct(z["brno"].mean(), 0)),
            ("Z Jihomoravského kraje", pct(1 - z["mimo_jmk"].mean(), 0)),
            ("Z jiných krajů", pct(z["mimo_jmk"].mean(), 1)),
            ("Přijelo přímo z domova", pct((z["rezidenti_navic"] / z["prijezdy_navic"]).mean(), 0))))
    popis_mimo = ("Podíl rezidentů z jiných krajů, průměr zápasů a 95% interval. V závorce počet zápasů; "
                  "u malých počtů je interval orientační.")
    telo = (
        karty_map()
        + "<div class=mriz2>"
        + graf_vzdalenost() + graf_profil()
        + graf_body("Kdy jezdí víc lidí z dálky: typ zápasu", popis_mimo, typy, "podíl z jiných krajů", 170)
        + graf_navsteva(z)
        + graf_body("Z jiných krajů podle sezóny", popis_mimo, sez, "podíl z jiných krajů", 110)
        + graf_body("Z Brna podle sezóny", "Podíl rezidentů z Brna, průměr zápasů a 95% interval.", sezb,
                    "podíl z Brna", 110)
        + graf_body("Z jiných krajů podle soupeře", popis_mimo, soup, "podíl z jiných krajů", 140)
        + graf_soupere(z, okr)
        + "</div>")
    vystup = DATA / "prehled.html"
    vystup.write_text(SABLONA.replace("@DLAZDICE@", dlazdice).replace("@TELO@", telo), encoding="utf-8")
    print(f"{vystup} ({vystup.stat().st_size / 1e6:.1f} MB)")


SABLONA = """<!doctype html>
<html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Odkud jezdí fanoušci HC Kometa Brno</title>
<style>
:root{color-scheme:light;--plocha:#fcfcfb;--pozadi:#f3f2ef;--text:#0b0b0b;--text2:#52514e;--mriz:#e4e3de;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--q1:#cde2fb;--q2:#9ec5f4;--q3:#6da7ec;--q4:#3987e5;--q5:#1c5cab;--q6:#0d366b;
--nejiste:#dedcd6;--prazdne:#f3f2ef;--obrys:#52514e}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--plocha:#1a1a19;--pozadi:#111110;--text:#f0efec;--text2:#c3c2b7;
--mriz:#383835;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--q1:#0d366b;--q2:#184f95;--q3:#256abf;--q4:#3987e5;--q5:#86b6ef;
--q6:#cde2fb;--nejiste:#3d3c39;--prazdne:#232321;--obrys:#c3c2b7}}
*{box-sizing:border-box}body{margin:0;background:var(--pozadi);color:var(--text);font:15px/1.45 system-ui,"Segoe UI",sans-serif}
main{max-width:1120px;margin:0 auto;padding:28px 16px 60px}h1{font-size:26px;margin:0 0 6px}
h2{font-size:17px;margin:0 0 4px}.popis{margin:0 0 12px;color:var(--text2);font-size:13.5px}
.varovani{background:var(--plocha);border-left:3px solid var(--text2);padding:10px 14px;margin:16px 0;font-size:14px}
.karta{background:var(--plocha);border-radius:10px;padding:18px;margin:16px 0;min-width:0}
.mriz2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr));gap:16px;align-items:start}
.mriz2 .karta{margin:0}.mriz2+.popis{margin-top:20px}svg{width:100%;height:auto;display:block}
.dlazdice{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.dl{background:var(--plocha);border-radius:10px;padding:12px 14px}.dl span{display:block;font-size:13px;color:var(--text2)}
.dl b{font-size:26px;font-weight:600}
.leg{display:flex;flex-wrap:wrap;gap:4px 16px;margin:0 0 10px;font-size:13px;color:var(--text2)}
.leg span{display:inline-flex;align-items:center;gap:6px}.leg i{width:12px;height:12px;border-radius:3px;display:inline-block}
.uz{stroke:var(--plocha);stroke-width:.5}.uz:hover{stroke:var(--text);stroke-width:1.5}
.obrys{fill:none;stroke:var(--obrys);stroke-width:.9;pointer-events:none}
.hala{fill:var(--s2);stroke:var(--plocha);stroke-width:2}.bod{stroke:var(--plocha);stroke-width:2}
.mriz{stroke:var(--mriz);stroke-width:1}.ref{stroke:var(--text2);stroke-width:1}.inter{stroke:var(--text2);stroke-width:2;stroke-linecap:round}
text{fill:var(--text2);font-size:12px}.popisek{fill:var(--text);font-size:12.5px}.stitek{font-size:12px}.osa{font-variant-numeric:tabular-nums}
details{margin-top:10px;font-size:13px}summary{cursor:pointer;color:var(--text2)}.tab{max-height:320px;overflow:auto;margin-top:8px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{text-align:left;padding:4px 8px;border-bottom:1px solid var(--mriz)}
#tip{position:fixed;pointer-events:none;background:var(--text);color:var(--plocha);padding:6px 9px;border-radius:6px;font-size:13px;display:none;max-width:280px;z-index:9}
#tip b{display:block}
</style></head><body><main>
<h1>Odkud jezdí fanoušci HC Kometa Brno</h1>
<p class=popis>Domácí zápasy ve Winning Group Aréně, leden 2024 – říjen 2026. Odhad z dat mobilní sítě O2 (Intiq), hexagon haly.</p>
<div class=varovani><b>Interní podklad, nezveřejňovat.</b> Licence dat Intiq není vyjasněná. Původ je jen u lidí, kteří přijeli
přímo z domova (asi polovina příchozích); kdo se cestou zastavil, v mapě chybí. Malé hodnoty zkresluje anonymizační šum.</div>
<div class=dlazdice>@DLAZDICE@</div>
@TELO@
<p class=popis>Zdroje: Intiq / O2 (mobilní data), hokej.cz (kalendář a návštěvnost), ČÚZK – RÚIAN (hranice).</p>
</main><div id=tip></div><script>
const t=document.getElementById('tip');
document.addEventListener('mousemove',e=>{const el=e.target.closest('[data-tip]');if(!el){t.style.display='none';return}
const [a,b]=el.dataset.tip.split('|');t.replaceChildren(Object.assign(document.createElement('b'),{textContent:a}),b||'');
t.style.display='block';const w=t.offsetWidth,h=t.offsetHeight;
t.style.left=Math.min(e.clientX+14,innerWidth-w-8)+'px';t.style.top=Math.max(8,Math.min(e.clientY+14,innerHeight-h-8))+'px'});
</script></body></html>
"""

if __name__ == "__main__":
    main()
