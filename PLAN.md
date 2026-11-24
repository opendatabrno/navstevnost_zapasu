# Plán projektu

## Fáze 0 – Průzkum platformy Intiq

Po přihlášení zjistit:

- **Prostorová jednotka** – lze vybrat přímo areál haly (polygon / čtverec mřížky / ZSJ), nebo jen větší území? Areál sousedí s výstavištěm, Mendlovým náměstím a obytnou zástavbou → riziko kontaminace.
- **Kategorie osob** – rezidenti / dojíždějící / návštěvníci / cizinci. Jak přesně je definován „dojíždějící“?
- **Původ** – granularita (obec / ORP / okres / kraj / stát), anonymizační prahy (od kolika osob se hodnota zobrazí).
- **Čas** – data jsou dostupná od 1. 1. 2024; lze volit rozlišení 15 minut → exportovat v nejjemnějším rozlišení zdroje, agregovat až při analýze. Ověřit, zda 15minutový krok nezvyšuje podíl hodnot skrytých anonymizací (hlavně u původu).
- **Export** – CSV/XLSX, API, nebo jen grafy v UI? → rozhoduje, zda stačí ruční export, nebo je potřeba automatizace (Playwright).
- **Licence** – smíme agregované výstupy publikovat jako open data?

👉 Pilot: jeden domácí zápas – ověřit, jak data vypadají, než se půjde do všech sezón.

## Fáze 1 – Kalendář zápasů

`data/zapasy.csv` – odehrané domácí zápasy Komety ve Winning Group Aréně od 1. 1. 2024 (od té doby má data Intiq), tj. sezóny 2023/24 (část) až 2026/27 (průběžně):

| sloupec | popis |
|---|---|
| datum, zacatek | datum a čas buly |
| souper | soupeř |
| faze | základní část / předkolo / play-off / Liga mistrů |
| navstevnost_oficialni | oficiální návštěva (hokej.cz, u Ligy mistrů hc-kometa.cz) |
| sezona, kolo, souper_plny_nazev, skore, stadion, zapas_id, zdroj | doplňkové údaje |

Kalendář sestavuje `scripts/stahni_zapasy.py`; zápasy Ligy mistrů jsou ručně v `data/zapasy_liga_mistru.csv`.

Doplňkově ostatní akce v hale (koncerty apod.) jako kontrolní skupina.

## Fáze 2 – Metodika

- **Uplift nad baseline:** přítomnost v okně zápasu (cca −2 h až +1 h od buly) po 15 minutách minus průměr stejného dne v týdnu a stejného 15minutového intervalu v týdnech bez akce. Tím se odfiltrují místní rezidenti a pracující.
- **Validace:** porovnání odhadu s oficiální návštěvností (kapacita haly cca 7 700).

## Fáze 3 – Výstupy

1. **Mapa původu fanoušků** – obce/okresy; podíl Brno / zbytek JMK / jiné kraje / zahraničí.
2. **Distribuce vzdáleností** – jak daleko lidé na hokej jezdí.
3. **Efekt soupeře** – hostující fanoušci (Zlín, Olomouc, Třinec, Pardubice…), derby vs. běžný zápas.
4. **Play-off vs. základní část**, víkend vs. všední den, čas začátku.
5. **Trend od ledna 2024** – mění se spádová oblast? (dvě celé sezóny + části 2023/24 a 2026/27)
6. **Časový profil příjezdů/odjezdů** (po 15 minutách) – podklad pro MHD a dopravu.
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
