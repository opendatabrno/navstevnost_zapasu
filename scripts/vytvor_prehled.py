"""Vytvoří z výsledků zpracuj_intiq.py přehled s mapou a grafy.

Výstup:  web/index.html (nasazuje se na GitHub Pages) a kopie
         data/processed/prehled.html (negitováno)
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
PRAHY_1000_OBCE = [0.5, 1, 2, 4, 6]  # hranice tříd na 1 000 obyvatel
PRAHY_1000_OKRESY = [0.02, 0.05, 0.25, 1, 2]
MESTA = ("Blansko", "Vyškov", "Břeclav", "Znojmo", "Třebíč", "Prostějov", "Hodonín", "Boskovice",
         "Tišnov", "Ivančice", "Kyjov", "Velké Meziříčí", "Mikulov")  # popisky v mapě
MIN_OBYVATEL_ZEBRICEK = 2000
MIN_OBYVATEL = 500  # menší obce se na 1 000 obyvatel nehodnotí
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
    return (f'<section class="karta {cls}"><h3>{esc(nadpis)}</h3><p class=popis>{esc(popis)}</p>'
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


def trida(x: float, prahy: list[float]) -> int:
    return 1 + sum(x >= p for p in prahy)


def mapa(g: gpd.GeoDataFrame, w: int, obrysy: gpd.GeoDataFrame, popis: str,
         sloupec: str = "podil_prumer", prahy: list[float] = PRAHY,
         kruhy: tuple[int, ...] = (), mesta: tuple[str, ...] = ()) -> str:
    na1000 = sloupec == "na1000"
    x0, y0, x1, y1 = g.total_bounds
    m = w / (x1 - x0)
    h = round((y1 - y0) * m)

    def fx(x):
        return (x - x0) * m

    def fy(y):
        return (y1 - y) * m

    o = []
    for r in g.itertuples():
        h1 = getattr(r, sloupec)
        hodnota = f"{cz(h1, 2)} na 1 000 obyvatel" if na1000 else pct(h1, 2)
        if r.spolehlive and not (na1000 and r.obyvatel < MIN_OBYVATEL):
            fill, stav = f"var(--q{trida(h1, prahy)})", hodnota
        elif r.ma_data:
            fill, stav = "var(--nejiste)", "málo dat, hodnotu neuvádíme"
        else:
            fill, stav = "var(--prazdne)", "bez příjezdů"
        o.append(f'<path d="{cesta(r.geometry, fx, fy)}" fill="{fill}" class=uz '
                 f'data-tip="{esc(r.nazev)}|{stav}"/>')
    for r in obrysy.itertuples():
        o.append(f'<path d="{cesta(r.geometry, fx, fy)}" class=obrys />')
    hala = gpd.GeoSeries(gpd.points_from_xy([HALA[0]], [HALA[1]]), crs=4326).to_crs(5514).iloc[0]
    for km in kruhy:
        r = km * 1000 * m
        o.append(f'<circle cx="{fx(hala.x):.1f}" cy="{fy(hala.y):.1f}" r="{r:.1f}" class=kruh />'
                 f'<text x="{fx(hala.x) - r:.1f}" y="{fy(hala.y) + 5:.1f}" class=km text-anchor=middle>{km} km</text>')
    # stejnojmenných obcí je víc, popisek patří největší
    for r in g[g["nazev"].isin(mesta)].sort_values("obyvatel").drop_duplicates("nazev", keep="last").itertuples():
        trida_popisku = "mesto" if mesta.index(r.nazev) < 7 else '"mesto maly"'
        b = r.geometry.representative_point()
        o.append(f'<text x="{fx(b.x):.1f}" y="{fy(b.y):.1f}" class={trida_popisku} text-anchor=middle>{esc(r.nazev)}</text>')
    o.append(f'<circle cx="{fx(hala.x):.1f}" cy="{fy(hala.y):.1f}" r="7" class=hala data-tip="Winning Group Arena|"/>')
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
    o = pd.read_csv(ROOT / "data" / "obyvatele.csv")
    o = o[o["uroven"] == nazev]
    # okresy mají v ČSÚ jiné kódy než v RÚIAN, názvy se shodují
    if nazev == "okresy":
        g = g.merge(o[["nazev", "obyvatel"]], on="nazev", how="left")
    else:
        g["kod"] = g["kod"].astype(int)
        g = g.merge(o.assign(kod=o["kod"].astype(int))[["kod", "obyvatel"]], on="kod", how="left")
    if g["obyvatel"].isna().any():
        raise ValueError(f"{nazev}: chybí obyvatelé u {g.loc[g['obyvatel'].isna(), 'nazev'].tolist()}")
    # typický zápas: průměrný počet rezidentů navíc rozdělený podle průměrných podílů
    na_zapas = pd.read_csv(DATA / "zapasy_odhad.csv")["rezidenti_navic"].mean()
    g["na1000"] = g["podil_prumer"] * na_zapas / g["obyvatel"] * 1000
    return g


def legenda_1000(prahy: list[float]) -> str:
    f = [cz(x, 2).rstrip("0").rstrip(",") for x in prahy]
    pol = [(f"do {f[0]}", "var(--q1)")]
    pol += [(f"{f[i]} – {f[i + 1]}", f"var(--q{i + 2})") for i in range(4)]
    pol += [(f"{f[4]} a víc", "var(--q6)"), ("málo dat nebo obyvatel", "var(--nejiste)"),
            ("bez příjezdů", "var(--prazdne)")]
    return legenda(pol)


def legenda_mapy() -> str:
    b = [0, *PRAHY]
    pol = [(f"do {pct(b[1], 2)}", "var(--q1)")]
    pol += [(f"{pct(b[i], 2)} – {pct(b[i + 1], 2)}", f"var(--q{i + 1})") for i in range(1, 5)]
    pol += [(f"{pct(b[5], 0)} a víc", "var(--q6)"), ("málo dat", "var(--nejiste)"),
            ("bez příjezdů", "var(--prazdne)")]
    return legenda(pol)


def zebricek(d: pd.DataFrame, sloupec: str, fmt, nadpis: str) -> str:
    d = d.nlargest(10, sloupec)
    mx = d[sloupec].max()
    return f"<h3>{esc(nadpis)}</h3><ol class=zeb>" + "".join(
        f'<li><span>{esc(r.nazev)}</span><span>{fmt(getattr(r, sloupec))}</span>'
        f'<i style="width:{100 * getattr(r, sloupec) / mx:.1f}%"></i></li>' for r in d.itertuples()) + "</ol>"


def prepinac(klic: str, polozky: list[tuple[str, str]]) -> str:
    return "<div class=prep>" + "".join(
        f'<button type="button" data-k="{klic}" data-v="{v}">{esc(n)}</button>' for v, n in polozky) + "</div>"


def karta_map() -> str:
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
    ramec = box(*g.total_bounds).intersection(hala.buffer(OKRUH_M + 1500))
    obrys = okresy[okresy.intersects(ramec)].copy()
    obrys["geometry"] = obrys.geometry.make_valid().boundary.intersection(ramec)

    def panel(uzemi: str, ukazatel: str) -> str:
        na1000 = ukazatel == "na1000"
        d = g if uzemi == "okoli" else okr
        sl = "na1000" if na1000 else "podil_prumer"
        prahy = PRAHY if not na1000 else PRAHY_1000_OBCE if uzemi == "okoli" else PRAHY_1000_OKRESY
        if uzemi == "okoli":
            m = mapa(d, 1000, obrys, "Mapa okolí Brna", sl, prahy, (20, 50), MESTA)
        else:
            m = mapa(d, 1000, okr.iloc[:0], "Mapa okresů Česka", sl, prahy)
        hod = d[d["spolehlive"]]
        if na1000:
            hod = hod[hod["obyvatel"] >= MIN_OBYVATEL]
            pozn = ("Lidé, kteří přijeli na typický zápas přímo z domova, na 1 000 obyvatel (1. 1. 2026). "
                    "Skutečná účast je vyšší, protože měříme asi polovinu příchozích. Poloha v síti je hrubá "
                    f"a sousední obce se můžou prolínat; obce pod {MIN_OBYVATEL} obyvatel nehodnotíme.")
            tab = tabulka(["Území", "Obyvatel", "Na 1 000"],
                          [[r.nazev, cz(r.obyvatel, 0), cz(r.na1000, 2)] for r in hod.nlargest(40, sl).itertuples()])
        else:
            pozn = ("Podíl na všech, kdo přijeli přímo z domova. Průměr zápasů, každý má stejnou váhu. "
                    "Větší území mají přirozeně víc lidí.")
            tab = tabulka(["Území", "Podíl"],
                          [[r.nazev, pct(r.podil_prumer, 2)] for r in hod.nlargest(40, sl).itertuples()])
        if na1000 and uzemi == "okoli":  # malé obce kolísají, do žebříčku jen větší
            zeb = zebricek(hod[hod["obyvatel"] >= MIN_OBYVATEL_ZEBRICEK], sl, cz,
                           f"Nejvíc, nad {cz(MIN_OBYVATEL_ZEBRICEK, 0)} obyvatel")
        else:
            zeb = zebricek(hod, sl, cz if na1000 else pct, "Nejvíc")
        leg = legenda_1000(prahy) if na1000 else legenda_mapy()
        return (f'<div class=panel data-m="{uzemi}-{ukazatel}"><div class=vlevo>{leg}{m}</div>'
                f"<div>{zeb}"
                f"<p class=popis>{esc(pozn)}</p>{tab}</div></div>")

    return ("<div class=karta><div class=ovl>"
            + prepinac("uzemi", [("okoli", "Brno a okolí"), ("cesko", "Celé Česko")])
            + prepinac("ukazatel", [("podil", "Podíl fanoušků"), ("na1000", "Na 1 000 obyvatel")]) + "</div>"
            + "".join(panel(u, k) for u in ("okoli", "cesko") for k in ("podil", "na1000")) + "</div>")


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
        for j, (sl, barva, jm) in enumerate((("navic", "--s1", "Přímo z domova"), ("nav", "--s2", "Odjinud"))):
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
                 "Podíl příjezdů podle vzdálenosti. U lidí, kteří nepřijeli z domova, jde o poslední "
                 "zastávku, ne o bydliště.",
                 legenda([("Přímo z domova", "var(--s1)"), ("Odjinud (poslední zastávka)", "var(--s2)")])
                 + svg(w, h, o, "Sloupcový graf vzdáleností"),
                 tabulka(["Pásmo (km)", "Přímo z domova", "Odjinud"], radky))


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
                 "Příjezdy do okolí haly po 15 minutách, průměr zápasů. Běžný provoz tu "
                 "není odečtený; síť telefon zaznamená typicky jednou za 30 minut.",
                 svg(w, h, o, "Sloupcový graf příjezdů v čase"),
                 tabulka(["Interval od buly (min)", "Podíl příjezdů"],
                         [[f"{k:+d} až {k + 15:+d}", pct(v)] for k, v in pod.items()]))


def graf_body(nadpis: str, popis: str, skupiny: list[tuple[str, pd.Series]], osa: str, sirka_stitku: int = 130,
              jednotka: str = "Zápasů") -> str:
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
              f'data-tip="{esc(n)}, {jednotka.lower()}: {pocet}|{pct(a)}{rozsah}"/>')
    o += f'<text x="{(w + x0) / 2}" y="{dole + 36}" class=osa text-anchor=middle>{esc(osa)}</text>'
    return karta(nadpis, popis, svg(w, h, o, nadpis),
                 tabulka(["Skupina", jednotka, "Průměr", "± 95 %"],
                         [[n, p, pct(a), "–" if np.isnan(c) else pct(c)] for n, p, a, c in st]))


def skupina_akce(typ) -> str:
    if typ == "univerzitní hokej":
        return "Univerzitní hokej"
    return {"koncert": "Koncerty", "MMA": "MMA (OKTAGON)"}.get(typ, "Neurčené akce")


def grafy_akci(z: pd.DataFrame) -> str:
    """Kontrolní skupina: zápasy Komety proti jiným akcím ve stejné hale."""
    ak = pd.read_csv(DATA / "akce_odhad.csv")
    ak["sk"] = ak["typ"].map(skupina_akce)
    okr = pd.read_csv(DATA / "akce_okresy.csv")
    k = okr.pivot_table(index="datum", columns="kraje", values="navic", aggfunc="sum").fillna(0)
    ak["mimo_jmk"] = (1 - k["Jihomoravský kraj"] / k.sum(axis=1)).reindex(ak["datum"]).to_numpy()
    jine = ak[ak["sk"] != "Univerzitní hokej"]  # univerzitní derby je také hokej, ale bez Komety
    sk = [("Zápasy Komety", z["mimo_jmk"]), ("Všechny jiné akce", jine["mimo_jmk"])] + [
        (n, ak.loc[ak["sk"] == n, "mimo_jmk"])
        for n in ("Koncerty", "MMA (OKTAGON)", "Neurčené akce", "Univerzitní hokej")]
    body = graf_body(
        "Kolik lidí je z jiných krajů",
        "Podíl lidí z jiných krajů, průměr akcí a 95% interval. Jiné akce jsou určené z dat "
        "(hodně lidí v hale ve dni bez zápasu), druh je doložený jen u části. „Všechny jiné akce“ "
        "jsou bez univerzitního hokeje. U 2–3 akcí je interval jen orientační.",
        sk, "podíl z jiných krajů", 170, "Akcí")

    poradi = ["(-0.001, 1.0]", "(1.0, 3.0]", "(3.0, 8.0]", "(8.0, 20.0]", "(20.0, 50.0]",
              "(50.0, 100.0]", "(100.0, 1000.0]"]
    nazvy = ["do 1 km", "1–3", "3–8", "8–20", "20–50", "50–100", "nad 100"]
    pod = {}
    for jm, soubor, dny in (("Zápasy Komety", "zapasy", None), ("Jiné akce", "akce", set(jine["datum"]))):
        d = pd.read_csv(DATA / f"{soubor}_vzdalenost.csv")
        if dny is not None:
            d = d[d["datum"].isin(dny)]
        m = d.pivot(index="datum", columns="pasmo_km", values="navic").fillna(0)[poradi]
        pod[jm] = m.div(m.sum(axis=1), axis=0).mean()
    w, h, x0, y0, y1, mx = 520, 300, 46, 20, 250, 0.4

    def fy(v):
        return y1 - v / mx * (y1 - y0)

    o = osa_y([0, .1, .2, .3, .4], fy, x0, w - 6, lambda q: pct(q, 0))
    krok = (w - 6 - x0) / len(poradi)
    for i, pasmo in enumerate(poradi):
        for j, (jm, barva) in enumerate((("Zápasy Komety", "--s1"), ("Jiné akce", "--s3"))):
            v = max(pod[jm][pasmo], 0)
            x, t = x0 + i * krok + krok / 2 - 21 + j * 22, fy(v)
            rr = min(4, y1 - t)
            o += (f'<path d="M{x:.1f},{y1}V{t + rr:.1f}q0,-{rr:.1f} {rr:.1f},-{rr:.1f}h{20 - 2 * rr:.1f}'
                  f'q{rr:.1f},0 {rr:.1f},{rr:.1f}V{y1}Z" fill="var({barva})" '
                  f'data-tip="{nazvy[i]} – {jm}|{pct(v)}"/>')
        o += f'<text x="{x0 + (i + .5) * krok:.1f}" y="{y1 + 18}" class=osa text-anchor=middle>{nazvy[i]}</text>'
    o += f'<text x="{(w + x0) / 2}" y="{y1 + 38}" class=osa text-anchor=middle>vzdálenost od haly (km)</text>'
    vzd = karta(
        "Jak daleko lidé na akce jezdí",
        "Podíl lidí podle vzdálenosti bydliště, průměr akcí. Jiné akce jsou bez univerzitního hokeje.",
        legenda([("Zápasy Komety", "var(--s1)"), ("Jiné akce", "var(--s3)")])
        + svg(w, h, o, "Sloupcový graf vzdáleností pro hokej a jiné akce"),
        tabulka(["Pásmo (km)", "Zápasy Komety", "Jiné akce"],
                [[n, pct(pod["Zápasy Komety"][q]), pct(pod["Jiné akce"][q])] for n, q in zip(nazvy, poradi)]))
    return body + vzd


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
                 "Lidé, kteří na zápas vyjeli z okresu soupeře. "
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
                 "Lidé navíc proti běžnému dni ve špičce zápasu. Odhad je soustavně nižší a jeho "
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

    popis_mimo = ("Podíl lidí z jiných krajů, průměr zápasů a 95% interval. V závorce počet zápasů; "
                  "u malých počtů je interval orientační.")
    brno_p, mimo_p = z["brno"].mean(), z["mimo_jmk"].mean()
    casti = [("z Brna", brno_p, "#ffffff"), ("ze zbytku Jihomoravského kraje", 1 - brno_p - mimo_p, "#6da7ec"),
             ("z jiných krajů", mimo_p, "#eb6834")]
    skala = ("<div class=skala><div class=pruh>"
             + "".join(f'<i style="flex:{p:.4f};background:{b}"></i>' for _, p, b in casti) + "</div><div class=pop>"
             + "".join(f'<div style="--b:{b}"><b>{pct(p, 0)}</b>{esc(n)}</div>' for n, p, b in casti) + "</div></div>")

    vz = pd.read_csv(DATA / "zapasy_vzdalenost.csv")
    vz = vz.pivot(index="datum", columns="pasmo_km", values="navic").fillna(0)
    vz = vz.div(vz.sum(axis=1), axis=0).mean()
    do8 = vz[["(-0.001, 1.0]", "(1.0, 3.0]", "(3.0, 8.0]"]].sum()
    nad50 = vz[["(50.0, 100.0]", "(100.0, 1000.0]"]].sum()
    host = okr.pivot_table(index="datum", columns="okresy", values="navic_vse", aggfunc="sum")
    host = host.reindex(z["datum"]).fillna(0)
    hosti = [(o, host.loc[(z["souper"] == s).to_numpy(), o].mean(), host.loc[(z["souper"] != s).to_numpy(), o].mean())
             for s, o in OKRES_SOUPERE.items() if o in host]
    okres, na, jinde = max(hosti, key=lambda t: t[1])
    ak = pd.read_csv(DATA / "akce_odhad.csv")
    ak = ak.loc[ak["typ"] != "univerzitní hokej", "datum"]
    ako = pd.read_csv(DATA / "akce_okresy.csv")
    ako = ako.pivot_table(index="datum", columns="kraje", values="navic", aggfunc="sum").fillna(0).loc[ak]
    ak_mimo = (1 - ako["Jihomoravský kraj"] / ako.sum(axis=1)).mean()
    po, zc = dict(typy)["Play-off a předkolo"].mean(), dict(typy)["Základní část"].mean()

    def kapitola(kod: str, nadpis: str, perex: str, obsah: str) -> str:
        return f'<section class=kap id="{kod}"><h2>{esc(nadpis)}</h2><p class=perex>{perex}</p>{obsah}</section>'

    def mriz(*karty: str) -> str:
        return "<div class=mriz2>" + "".join(karty) + "</div>"

    zvyr = (f'<div class="karta zvyr"><div class=dvoj><div><b>{pct(po)}</b><span>play-off a předkolo</span></div>'
            f"<div><b>{pct(zc)}</b><span>základní část</span></div></div>"
            "<p>Takový podíl lidí, kteří přijeli přímo z domova, bydlí v jiném kraji.</p></div>")
    jak = ("<div class=karta><h3>Na co si dát pozor</h3><p class=popis>Než z čísel něco vyvodíte.</p><ul class=body>"
           "<li>Jde o odhad z dat jednoho operátora, ne o sčítání diváků.</li>"
           "<li>Počítáme rozdíl proti běžným dnům bez zápasu a bez jiné akce v hale.</li>"
           "<li>Bydliště známe jen u lidí, kteří přijeli přímo z domova. To je asi polovina příchozích; "
           "kdo se cestou zastavil, v mapě chybí.</li>"
           "<li>Malé hodnoty zkresluje anonymizační šum, proto je u území s málo daty neuvádíme.</li>"
           "<li>Úroveň odhadu se v čase mění, takže mezi sezónami porovnávejte podíly, ne počty.</li></ul></div>")
    telo = (
        kapitola("mapa", "Odkud lidé jezdí",
                 f"Z Jihomoravského kraje je <b>{pct(1 - mimo_p, 0)}</b> fanoušků, jen ze samotného Brna "
                 f"<b>{pct(brno_p, 0)}</b>. Najeďte na obec, městskou část nebo okres.", karta_map())
        + kapitola("cesta", "Jak daleko a kdy",
                   f"Do 8 km od haly bydlí <b>{pct(do8, 0)}</b> lidí, kteří přijeli přímo z domova. "
                   f"Z větší dálky než 50 km jich přijíždí <b>{pct(nad50, 0)}</b>.",
                   mriz(graf_vzdalenost(), graf_profil()))
        + kapitola("zapasy", "Kdy přijede víc lidí z dálky",
                   "Srovnání podle typu zápasu a podle sezóny.",
                   mriz(graf_body("Podle typu zápasu", popis_mimo, typy, "podíl z jiných krajů", 170), zvyr,
                        graf_body("Z jiných krajů podle sezóny", popis_mimo, sez, "podíl z jiných krajů", 110),
                        graf_body("Z Brna podle sezóny", "Podíl lidí z Brna, průměr zápasů a 95% interval.", sezb,
                                  "podíl z Brna", 110)))
        + kapitola("souperi", "Soupeři a hosté",
                   f"Hosté jsou v datech vidět. Nejvíc jich přijíždí z okresu {esc(okres)}: průměrně <b>{cz(na, 0)}</b> "
                   f"příjezdů navíc na zápas s tamním týmem, na ostatní zápasy <b>{cz(jinde, 0)}</b>.",
                   mriz(graf_body("Z jiných krajů podle soupeře", popis_mimo, soup, "podíl z jiných krajů", 140),
                        graf_soupere(z, okr)))
        + kapitola("akce", "Hokej a jiné akce v hale",
                   f"Na koncertech a dalších akcích je z jiných krajů <b>{pct(ak_mimo, 0)}</b> lidí, "
                   f"na zápasech Komety <b>{pct(mimo_p, 0)}</b>.", mriz(grafy_akci(z)))
        + kapitola("odhad", "Jak výsledky číst",
                   "Odhad z mobilní sítě je nižší než oficiální návštěvnost, proto pracujeme hlavně s podíly.",
                   mriz(graf_navsteva(z), jak)))
    vystup = ROOT / "web" / "index.html"
    stranka = (Path(__file__).with_name("sablona.html").read_text(encoding="utf-8")
               .replace("@POCET@", str(len(z))).replace("@SKALA@", skala).replace("@TELO@", telo))
    for soubor in (vystup, DATA / "prehled.html"):
        soubor.write_text(stranka, encoding="utf-8")
    print(f"{vystup} ({vystup.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
