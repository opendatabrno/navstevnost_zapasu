# Návštěvnost zápasů – HC Kometa Brno

Analýza návštěvnosti domácích zápasů HC Kometa Brno ve Winning Group Aréně na základě dat o pohybu obyvatel z platformy [Intiq](https://auth.iq.intiq.app/) (data z mobilní sítě).

**Cíl:** zjistit, odkud fanoušci na zápasy dojíždějí, jak se to liší podle soupeře, fáze sezóny a času, a jak se to vyvíjí od ledna 2024, odkdy jsou data dostupná (v 15minutovém rozlišení).

Web: https://opendatabrno.github.io/navstevnost_zapasu/

Podrobný plán viz [PLAN.md](PLAN.md).

## Struktura

```
data/raw/        – surové exporty z Intiq a stažené hranice (negitované, viz licence)
data/processed/  – agregace po zápasech a územích (negitované, viz licence)
data/zapasy.csv  – kalendář domácích zápasů
data/zapasy_liga_mistru.csv – ručně doplněné zápasy Ligy mistrů
data/akce.csv    – doložené jiné akce v hale (koncerty, MMA, univerzitní hokej)
data/obyvatele.csv – počty obyvatel (ČSÚ, MV ČR)
scripts/         – stahování, zpracování a vytvoření webu
notebooks/       – analýzy (zatím prázdné)
web/             – vygenerovaná statická stránka (zveřejněná ve větvi gh-pages)
```

## Postup

```
python scripts/stahni_zapasy.py      # kalendář zápasů (hokej.cz)
python scripts/stahni_hranice.py     # hranice území (ČÚZK – RÚIAN)
python scripts/stahni_obyvatele.py   # počty obyvatel
python scripts/zpracuj_intiq.py      # potřebuje exporty z Intiq v data/raw/intiq/
python scripts/vytvor_prehled.py     # vytvoří web/index.html
python -m http.server 8123 --bind 127.0.0.1 --directory web
```

Web pak běží na vlastním počítači na adrese http://127.0.0.1:8123/. Potřebné balíčky: pandas, geopandas, h3, openpyxl, tzdata.

## Stav

- [x] Fáze 0 – průzkum platformy Intiq
- [x] Fáze 1 – kalendář zápasů a doložené jiné akce v hale
- [x] Fáze 2 – metodika: rozdíl proti běžným dnům, porovnání s oficiální návštěvností
- [x] Fáze 3 – mapy původu, vzdálenosti, soupeři, typ zápasu, sezóny, profil příjezdů, hokej a jiné akce
- [ ] Fáze 3 – profil odjezdů, podklad k debatě o nové hale
- [x] Fáze 4 – statický web (větev `gh-pages`)
- [ ] Open data (CSV) – čeká na vyjasnění licence dat Intiq

Surové exporty a podrobné agregace z Intiq v repozitáři nejsou, zveřejněné jsou jen souhrnné výsledky na webu.
