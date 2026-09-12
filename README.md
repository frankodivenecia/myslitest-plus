# MyslivecZkouška

Webová appka pro přípravu na **ústní mysliveckou zkoušku** (myslivecký kurz LDF
MENDELU). Přihlášený uživatel si prochází **1310 otázek ze 7 předmětů**, ke každé
si píše **vlastní odpověď**, značí si **těžké** otázky a může si vše **vytisknout
do PDF**. Běží na <https://myslivost.b4u.cz>.

Postavené na skvělém open-source projektu **MyslíTest** od Honzy (Jana) Zdráhala —
viz [Kredit a zdroj](#kredit-a-zdroj) níže. Odtud pochází celá sada otázek
i vzorových odpovědí.

## Co umí

- **Účty** — otevřená registrace, přihlášení, **reset hesla e-mailem** (odkaz
  platný 1 h, jednorázový).
- **Editor odpovědí** — u každé otázky si píšeš vlastní odpověď (Markdown).
  Odpovědi jsou **soukromé per-user**, nikdo jiný je nevidí.
- **Vzor (master)** — původní odpověď z předlohy se zobrazuje pod editorem jen
  ke čtení; tlačítko „Převzít vzor" ji zkopíruje jako výchozí text. Vzor se nikdy
  nepřepíše.
- **Těžké otázky** — označení vlaječkou ⚑, samostatný pohled „jen těžké".
- **Dashboard** — souhrn: celkem otázek, podle typu (A/B/C), kolik máš
  zodpovězeno a kolik označeno jako těžké.
- **Klikatelná navigace** — předmět → karta/okruh → otázka, s postupem u každé
  karty.
- **Tisk do PDF** — tiskne **jen tvoje odpovědi**, ve třech řezech: celý předmět,
  jednotlivá karta/okruh, nebo jen těžké. (V prohlížeči Ctrl+P → Uložit jako PDF.)

## Stack

FastAPI · SQLAlchemy 2.0 · PostgreSQL · Jinja2 · bcrypt · uvicorn za nginx
(reverse proxy + TLS) pod systemd. Lokální vývoj běží na SQLite (přepíná se přes
`DATABASE_URL`).

## Datový model

- **Sdílený katalog (jen ke čtení):** `subjects` → `cards` → `questions`.
  U otázky je `reference_md` = původní vzorová odpověď z předlohy. „Typ A/B/C" =
  blok otázky.
- **Per-user (soukromé):** `user_questions` — vlastní `answer_md` a značka `hard`
  ke každé otázce.

Katalog se plní z adresáře `content/predmet/**` importérem
(`python -m app.importer`); `content/` je tedy jen zdroj (seed), aplikace čte z DB.

## Struktura

```
app/
  config.py        nastavení z prostředí (.env)
  models.py        SQLAlchemy modely + engine/session
  importer.py      import katalogu z content/ do DB (--dry-run pro statistiky)
  auth.py          hashování hesel, session, CSRF, reset-token
  mailer.py        odesílání e-mailů (SMTP)
  main.py          FastAPI app, middleware, routery
  routers/         auth · dashboard · questions · printing
templates/         Jinja2 šablony
static/app.css     styl
content/predmet/   zdroj otázek a vzorových odpovědí (seed)
DOCUMENTATION.md   podrobnosti k architektuře a nasazení
```

## Provoz

Konfigurace přes `.env` (nikdy necommitovat):

```
SECRET_KEY=...
DATABASE_URL=postgresql+psycopg://myslitest:HESLO@localhost/myslitest
SESSION_HTTPS_ONLY=true
BASE_URL=https://myslivost.b4u.cz
SMTP_HOST=... SMTP_PORT=587 SMTP_USER=... SMTP_PASS=... MAIL_FROM=...
```

Bring-up a běžný postup (pull → import → restart služby) jsou popsané
v [`DOCUMENTATION.md`](DOCUMENTATION.md). Služba běží pod systemd
(`myslitest.service`), takže je online i bez otevřené SSH session.

## Kredit a zdroj

Tento projekt vychází z **MyslíTest** od **Honzy (Jana) Zdráhala**:

- Web: <https://panjan.gitlab.io/myslitest/>
- Zdroj: <https://gitlab.com/panjan/myslitest>

Z jeho projektu pochází **kompletní sada otázek a vzorových odpovědí**
(`content/predmet/`), které tato appka importuje a zobrazuje jako vzor ke čtení.
Velké díky Honzovi za odvedenou práci. Otázky a odpovědi jsou jeho dílem —
respektuj prosím podmínky uvedené v jeho repozitáři.

MyslivecZkouška k tomu přidává víceuživatelskou vrstvu: účty, vlastní odpovědi,
značení těžkých otázek, dashboard a tisk do PDF.
