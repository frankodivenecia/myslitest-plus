# Myslitest

Otázky k ústní zkoušce z myslivosti, kterou se uzavírá myslivecký kurz
Ústavu ochrany lesů a myslivosti LDF MENDELU, ročník 2025/2026.

Web běží na <https://panjan.gitlab.io/myslitest/>.

## Obsah

Píše se jen markdown v `content/`, jinde se needituje:

- `content/predmet/<předmět>/<karta>/_index.md` — otázky jedné karty:
  `## nadpis bloku` a pod ním číslované otázky; hlavička jen tam, kde je
  potřeba ručně nasměrovat odkaz na myslivecke-zkousky.cz (viz níž)
- `content/predmet/<předmět>/<karta>/<otázka>.md` — odpověď; leží vedle karty
  a jmenuje se podle místa otázky: písmeno je blok, číslo pořadí v něm, takže
  `b3.md` je třetí otázka bloku B
- `content/predmet/<předmět>/<karta>/<obrázek>.jpg` — fotka k odpovědi; leží
  také vedle karty, takže ji můžou sdílet odpovědi na několik otázek, a píše
  se na ni `![](../soubor.jpg)`
- `content/predmet/<předmět>/_index.md` — název předmětu, pořadí a to, jestli
  se dělí na karty, nebo na okruhy
- `content/_index.md` — úvodní strana

Odpověď, kterou napsala AI a člověk ji zatím nepročetl, má v hlavičce
`unreviewed: true`. Stránka pak nad odpovědí nese varování a vyzve čtenáře, ať
je první, kdo ji ověří. Kdo odpověď ověří, řádek smaže — tím varování zmizí.

Svůj soubor má každá otázka, i ta nezodpovězená — ten je zatím prázdný a čeká,
až ho někdo vyplní. Psát se začíná rovnou do něj: první odstavec je věta, kterou
se u zkoušky odpovídá, za ním zbytek textu a nakonec `## Zdroje` s číslovaným
seznamem pramenů, na které text odkazuje `[1]`; do hlavičky patří `description`,
věta pro vyhledávače. Stránka nezodpovězené otázky existuje a je na ní vidět, že
odpověď chybí, ale karta na ni neodkazuje, aby to nevypadalo, že je hotová.
Odkaz `[text otázky](b3/index.html)` se do karty připíše, až odpověď stojí.

Nová karta je nový adresář s `_index.md` a s prázdným souborem pro každou
otázku. Čísla otázek, kódy bloků (`VII/A/11`), římská čísla předmětů, počty
otázek na kartě i v předmětu, odkazy mezi stránkami a titulky se dopočítávají
ze struktury a z pořadí — nepíšou se.

Obrázek musí být volně licencovaný — hledá se na Wikimedia Commons. Autor,
licence a odkaz na původní soubor patří do zdrojů pod odpovědí, stejně jako
u textu.

## Odkazy na myslivecke-zkousky.cz

Skoro celá sada je vypracovaná i na <https://www.myslivecke-zkousky.cz>. Tamní
stránka drží celý blok najednou, takže odkaz stojí pod blokem, ne u každé
otázky — pětkrát by vedl na totéž. Číslo stránky plyne přímo z kódu bloku:
`odpoved.php?ido=1` je I/A/1, `ido=420` je VII/C/20. Nikam se tedy nepíše.

Dvě věci z kódu neplynou a stojí v hlavičce karty pod klíčem `elsewhere`:

- Tamní web má prohozené nadpisy bloků VII/B/1 a VII/B/2. U karet 1 a 2
  předmětu Lov zvěře proto stojí `B:` s číslem stránky, na které opravdu jsou
  tytéž otázky.
- Péče o zvěř je u nás rozdělená na okruhy a otázky v nich jsou přeformulované
  a slité dohromady. Odkazuje se tam po otázkách: `"8": 217` znamená, že osmá
  otázka okruhu stojí na stránce 217. Otázka, která tam protějšek nemá, se
  neuvádí a odkaz nedostane.

## Generování

HTML dělá GitLab: po pushi do `master` spustí `.gitlab-ci.yml` Hugo

    hugo --destination public

a výsledek vystaví jako Pages. Nic vygenerovaného se necommituje, `public/`
je v `.gitignore`.

Lokálně není potřeba nic instalovat. Kdo si přesto chce web prohlédnout
u sebe a má Docker:

    docker run --rm -v "$PWD":/src -w /src -p 1313:1313 hugomods/hugo:0.165.0 \
      hugo server --bind 0.0.0.0

## Návštěvnost

Návštěvy počítá [Umami](https://cloud.umami.is/analytics/eu/websites/4018208c-ad3a-4276-b2c5-053783969dcb);
přehled je za přihlášením. Měřicí skript vkládá `_partials/analytics.html`
do hlavičky stránky, jeho adresa a `umamiWebsiteId` stojí v `hugo.toml`.
Vkládá se jen v produkčním sestavení, takže prohlížení u sebe se nepočítá,
a bez vyplněného ID se nevloží vůbec.

## Šablony

`layouts/` je jediné místo, kde je kód:

- `baseof.html` — obálka stránky, hlavička a patička
- `home.html`, `predmet/section.html` — úvodní strana a rejstřík předmětu
- `karta/section.html`, `karta/page.html` — karta s otázkami a stránka odpovědi
- `_partials/` — rozbor karty na bloky, místo otázky na kartě, součty, česká
  sazba a odkazy na myslivecke-zkousky.cz

`_partials/typography.html` sází českou typografii: nedělitelné mezery za
jednopísmennými předložkami, před pomlčkou, v datech, u zkratek, jednotek
a řádů tisíců. Kde je nedělitelná mezera potřeba nad rámec pravidel, píše se
do markdownu přímo (U+00A0).

Písmo, styl a skript leží v `static/` a Hugo je do webu jen kopíruje.
Odškrtávání naučených otázek v HTML není: kolečka u otázek i podíly
v rejstřících vyrábí `static/progress.js` a stav drží v localStorage
prohlížeče. Bez skriptu zůstane web plný text ke čtení, jen bez odškrtávání.

## Předloha

Naskenované soubory otázek, ze kterých web vychází, leží v `source/`.
Číslo v názvu je číslo předmětu z předlohy (Předmět I–VII), zbytek názvu
odpovídá adresáři předmětu v `content/predmet/`. Adresář `source/` se
nepublikuje — CI vystavuje jen vygenerované `public/`.

Otázky web přepisuje doslova. Výjimkou je pár zjevných překlepů předlohy,
které opravuje; číslování zůstává beze změny, aby odpovídalo předloze
u zkoušky.

## Písmo

Celý web sází [Literata](https://github.com/googlefonts/literata) (SIL OFL 1.1,
licence v `static/pismo/OFL.txt`).
