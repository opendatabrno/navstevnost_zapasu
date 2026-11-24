# Odkud jezdí fanoušci HC Kometa Brno

Web o tom, odkud lidé jezdí na domácí zápasy HC Kometa Brno ve Winning Group Aréně. Vychází z dat
o pohybu obyvatel z mobilní sítě (Intiq / O2) od ledna 2024.

- **Web:** https://opendatabrno.github.io/navstevnost_zapasu/
- **Kalendář zápasů:** [data/zapasy.csv](data/zapasy.csv)

## Co na webu najdete

| Část | Co ukazuje |
|---|---|
| Mapy původu | podíl fanoušků z městských částí Brna, obcí do 65 km a okresů Česka |
| Mapy na 1 000 obyvatel | odkud jezdí nejvíc lidí vůči velikosti území |
| Vzdálenost | jak daleko lidé na hokej jezdí |
| Čas příjezdu | kdy lidé před zápasem přijíždějí |
| Typ zápasu a sezóna | základní část, play-off, Liga mistrů, víkend, všední den, vývoj po sezónách |
| Soupeři a hosté | podíl lidí z jiných krajů a příjezdy z okresu soupeře |
| Odhad a oficiální návštěva | srovnání odhadu s oficiální návštěvností |
| Hokej a jiné akce | srovnání s koncerty a dalšími akcemi ve stejné hale |

## Data

| Soubor | Obsah | Zdroj |
|---|---|---|
| [`data/zapasy.csv`](data/zapasy.csv) | odehrané domácí zápasy ve Winning Group Aréně od ledna 2024: datum, začátek, soupeř, fáze, skóre, oficiální návštěva | hokej.cz, hc-kometa.cz |
| [`data/zapasy_liga_mistru.csv`](data/zapasy_liga_mistru.csv) | zápasy Ligy mistrů, součást kalendáře | hc-kometa.cz |
| [`data/akce.csv`](data/akce.csv) | doložené jiné akce v hale: koncerty, MMA, univerzitní hokej | odkaz u každé akce |
| [`data/obyvatele.csv`](data/obyvatele.csv) | počty obyvatel obcí, okresů a městských částí Brna | ČSÚ, MV ČR |

Surová data z mobilní sítě v repozitáři nejsou, na webu jsou jen souhrnné výsledky.

## Jak výsledky číst

- Jde o odhad z dat jednoho operátora, ne o sčítání diváků.
- Počítá se rozdíl proti běžným dnům bez zápasu a bez jiné akce v hale.
- Bydliště je známé jen u lidí, kteří přijeli přímo z domova. Kdo se cestou zastavil, v mapách chybí.
- Malé hodnoty zkresluje anonymizační šum, u území s málo daty se proto hodnota neuvádí.
- Úroveň odhadu se v čase mění, mezi sezónami se proto porovnávají podíly, ne počty.

## Licence

Kód: MIT (viz [LICENSE](LICENSE)). Hranice: RÚIAN, © ČÚZK, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.cs).
Ostatní data: podle zdrojů.
