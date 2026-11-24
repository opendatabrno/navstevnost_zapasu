# Plán projektu

## Fáze 0 – Průzkum platformy Intiq

Zdroj: uživatelská příručka INTIQ IQ Modules (SW 4.8.0) a prohlížení modulu Obyvatelstvo. Konkrétní hodnoty z Intiq sem nepatří, dokud není jasná licence.

| otázka | zjištění |
|---|---|
| **Prostorová jednotka** | Hexagony H3, nejjemněji rozlišení 9. Hala leží v `891e0695123ffff`, ten ale zahrnuje i okolní zástavbu (Křídlovická, Nové sady) → bez baseline nelze. |
| **Rezident × návštěvník** | Rezident = v kalendářním měsíci tráví v hexagonu nejvíc času v noci (každý má právě jeden). Návštěvník = v hexagonu je, ale rezidentem není. |
| **Přítomné** | Počet osob; delší interval je průměr 15minutových hodnot. |
| **Přijíždějící** | Počet cest osob, které v hexagonu stráví alespoň 15 min; delší interval je součet, opakované cesty se počítají. „Rezidenti“ přijeli z hexagonu, kde bydlí; „návštěvníci“ odjinud. „Pravidelní“ = alespoň 12× měsíčně. |
| **Vyjíždějící** | Počet cest zahájených v hexagonu. Definice kategorií je v příručce nejednoznačná a naměřené počty „rezidentů“ výrazně převyšují počet lidí, kteří v hexagonu bydlí → **pro původ fanoušků nepoužívat**, jen orientačně pro profil odjezdů. |
| **Původ** | Protější hexagon cesty. Oblast B je volitelná; bez ní jsou vidět cesty ze všech oblastí, i mimo Brno. |
| **Čas** | Od 1. 1. 2024, aktualizace měsíčně, zdroj po 15 minutách. Telefon se ale síti hlásí typicky každých 30 minut → 15minutový krok je jemnější než skutečná přesnost. |
| **Anonymizace** | Příručka nezmiňuje skrývání malých hodnot, ale differential privacy (šum); zkreslení hlavně u hodnot do 10. |
| **Export** | Z UI, vyžaduje oprávnění, vždy 15minutová data; velké exporty dělit na kratší období. CSV (čárka, UTF-8), řádek = zdrojový hexagon × cílový hexagon × 15 min, sloupce pro 4 kategorie; nulové řádky chybí. **Časy jsou v UTC** → převést na Europe/Prague (výjimka viz hodinový posun níže). Původ je hexagon H3 rozlišení 9, obec se doplní prostorovým spojením s RÚIAN. Stahování po čtvrtletích je spolehlivé (Přijíždějící i Přítomné). |
| **Licence** | Příručka ani veřejné zdroje ji neuvádějí → **otevřené**, před publikací dořešit. |

**Pilot** – dva domácí zápasy s rozdílnou návštěvou: Luleå 18. 11. 2025 (2 142 diváků) a finále s Pardubicemi 27. 4. 2025 (7 700). Přítomnost v okně zápasu na velikost návštěvy zřetelně reaguje; baseline zatím neodečtena.

**Z toho plyne**

- Velikost návštěvy odhadovat z **Přítomných** (návštěvníci).
- Původ odhadovat z **Přijíždějících, kategorie rezidenti** – jen u nich je původ zároveň bydliště. U návštěvníků je to jen předchozí zastávka (práce, hospoda, zastávka MHD). Zda jsou ti, kdo jedou přímo z domova, reprezentativní pro všechny, je potřeba ověřit.
- Původ kvůli šumu sčítat přes celé okno a přes více zápasů a agregovat do větších územních celků; jednotlivé 15minutové hodnoty pro malé hexagony nevykládat.

**Otevřené**

- **Hodinový posun:** Přijíždějící mají před 1. 3. 2025 v exportu místní čas označený jako UTC → před tímto datem značku neposouvat, od něj převádět z UTC. Přítomné jsou v UTC celou dobu. Ověřeno na zápasech; přesný den hranice leží mezi 25. 2. a 2. 3. 2025 (podle zápasů). Velikost posunu odpovídá zimnímu a letnímu času (+1 h / +2 h); samotné noci změny času jsou v datech nejasné, zápasů se ale netýkají.
- **Úroveň odhadu není v čase stejná:** poměr k oficiální návštěvě je v lednu–březnu 2024 vyšší než později → absolutní počty mezi sezónami neporovnávat, používat podíly nebo přepočet na oficiální návštěvu. Příčina neznámá.
- Extrapolaci na celou populaci příručka popisuje jen u dopravy; u obyvatelstva ji ověřit.
- Licence (viz tabulka).
- Většina hodnot v exportu je menší než 10, tedy v pásmu, kde šum zkresluje nejvíc → ověřit, jak se to projeví po sečtení přes více zápasů.

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

- **Uplift nad baseline:** přítomnost v okně zápasu (cca −3 h až +5 h od buly, aby zahrnulo příjezdy i odjezdy) po 15 minutách minus průměr stejného dne v týdnu a stejného 15minutového intervalu v týdnech bez akce. Tím se odfiltrují místní rezidenti a pracující.
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

- Data jednoho operátora (O2); měří se telefony, ne osoby, a chybí telefony přihlášené do sítě jiného operátora. Nutno uvádět u výsledků.
- Zahrnuta jsou jen data se souhlasem uživatele; lokalizace podle pokrytí signálem je méně přesná než GPS.
- Anonymizační šum zkresluje malé hodnoty → agregovat spíš po ORP/okresech.
- Překryv areálu s okolím → nutná baseline.
- Licence může omezit publikaci.
