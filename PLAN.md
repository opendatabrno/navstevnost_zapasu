# Plán projektu

## Fáze 0 – Průzkum platformy Intiq

Po přihlášení zjistit:

- **Prostorová jednotka** – lze vybrat přímo areál haly (polygon / čtverec mřížky / ZSJ), nebo jen větší území? Areál sousedí s výstavištěm, Mendlovým náměstím a obytnou zástavbou → riziko kontaminace.
- **Kategorie osob** – rezidenti / dojíždějící / návštěvníci / cizinci. Jak přesně je definován „dojíždějící“?
- **Původ** – granularita (obec / ORP / okres / kraj / stát), anonymizační prahy (od kolika osob se hodnota zobrazí).
- **Čas** – hodinová, nebo jen denní data? Hloubka historie (údajně ~5 let).
- **Export** – CSV/XLSX, API, nebo jen grafy v UI? → rozhoduje, zda stačí ruční export, nebo je potřeba automatizace (Playwright).
- **Licence** – smíme agregované výstupy publikovat jako open data?

👉 Pilot: jeden domácí zápas – ověřit, jak data vypadají, než se půjde do všech sezón.

## Fáze 1 – Kalendář zápasů

`data/zapasy.csv` – domácí zápasy Komety, sezóny 2021/22–2025/26:

| sloupec | popis |
|---|---|
| datum, zacatek | datum a čas buly |
| souper | soupeř |
| faze | základní část / předkolo / play-off |
| navstevnost_oficialni | oficiální návštěva (hokej.cz) |

Doplňkově ostatní akce v hale (koncerty apod.) jako kontrolní skupina.

## Fáze 2 – Metodika

- **Uplift nad baseline:** přítomnost v okně zápasu (cca −2 h až +1 h od buly) minus průměr stejného dne v týdnu a hodiny v týdnech bez akce. Tím se odfiltrují místní rezidenti a pracující.
- **Validace:** porovnání odhadu s oficiální návštěvností (kapacita haly cca 7 700).

## Fáze 3 – Výstupy

1. **Mapa původu fanoušků** – obce/okresy; podíl Brno / zbytek JMK / jiné kraje / zahraničí.
2. **Distribuce vzdáleností** – jak daleko lidé na hokej jezdí.
3. **Efekt soupeře** – hostující fanoušci (Zlín, Olomouc, Třinec, Pardubice…), derby vs. běžný zápas.
4. **Play-off vs. základní část**, víkend vs. všední den, čas začátku.
5. **Trend přes 5 sezón** – mění se spádová oblast?
6. **Časový profil příjezdů/odjezdů** – podklad pro MHD a dopravu.
7. **Hokej vs. koncerty** – liší se spádovost?
8. **Podklad k debatě o nové hale** – kde fanoušci bydlí.

## Fáze 4 – Technické řešení

- Python (pandas, geopandas), notebooky pro analýzu.
- Hranice obcí/okresů z RÚIAN (ČÚZK).
- Výstup: statická web stránka s interaktivní mapou a grafy + CSV jako open data.

## Rizika a omezení

- Data jednoho operátora extrapolovaná na populaci – nutno uvádět u výsledků.
- Anonymizační prahy skryjí malé obce → agregovat spíš po ORP/okresech.
- Překryv areálu s okolím → nutná baseline.
- Licence může omezit publikaci.
