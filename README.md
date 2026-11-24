# Návštěvnost zápasů – HC Kometa Brno

Analýza návštěvnosti domácích zápasů HC Kometa Brno ve Winning Group Aréně na základě dat o pohybu obyvatel z platformy [Intiq](https://auth.iq.intiq.app/) (data z mobilní sítě).

**Cíl:** zjistit, odkud fanoušci na zápasy dojíždějí, jak se to liší podle soupeře, fáze sezóny a času, a jak se to vyvíjí za posledních ~5 sezón.

Podrobný plán viz [PLAN.md](PLAN.md).

## Struktura

```
data/raw/        – surové exporty z Intiq (negitované, viz licence)
data/processed/  – agregace po zápasech a obcích (CSV)
data/zapasy.csv  – kalendář domácích zápasů
scripts/         – stahování a čištění dat
notebooks/       – analýzy
web/             – statická vizualizace (mapa, grafy)
```

## Stav

🚧 Plánování – čeká se na přístup do Intiq a ověření, jaká data platforma nabízí.
