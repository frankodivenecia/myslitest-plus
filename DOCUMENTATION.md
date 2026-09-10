# Myslitest-plus — dokumentace (zdroj pravdy)

> Na začátku každé session přečti tento soubor. Popisuje, co appka je, jak je
> postavená a v jakém pořadí se staví. Moduly se dělají jako atomické,
> nasaditelné celky.

## Co to je

Osobní studijní appka k ústní zkoušce z myslivosti (kurz LDF MENDELU).
**Katalog otázek je pevný a sdílený** (naimportovaný z původního Hugo obsahu),
**vše, co uživatel píše, je soukromé per-user** — vlastní odpovědi a vlastní
značky „těžká". Žádný obsah se mezi uživateli nesdílí.

Tok uživatele:
1. **Landing = login** (žádný veřejný front) + krátké „co to je" z README.
2. Po přihlášení → **Dashboard**: statistiky + vstup do **Otázek** (všechny,
   současný přehled) a do **Těžkých** (co si uživatel označil).
3. **Editor odpovědi** po výběru otázky (styl „příspěvek na nástěnku" z Dominia).
4. **Tisk** otázek+odpovědí po řezech: všechny A / všechny B / všechny C, nebo
   po předmětech I–VII (bloky), nebo po kartách (karta = A+B+C).

## Rozhodnutí (zamčeno)

- Těžká otázka = **per-user, v DB** (drží se po přihlášení, ne v localStorage).
- Odpovědi = **per-user, v DB** (každý si píše svoje).
- Registrace = **otevřená, bez schvalování**. Obsah není sdílený.
- Hugo statika se **retiruje** — `content/` zůstává jen jako zdroj pro import
  katalogu. `layouts/`, `.gitlab-ci.yml`, `static/progress.js` časem odejdou.

## Stack

FastAPI + PostgreSQL (SQLAlchemy 2.0) + Jinja2, na stejném Hetzner VPS jako
Dominium (host nginx + certbot, systemd, sdílený Postgres — nová DB `myslitest`).
Doména `myslivost.b4u.cz`. Auth se zvedne z Dominia.

Lokální vývoj běží na SQLite (bez DB serveru), produkce na Postgresu — přepíná
se přes `DATABASE_URL`.

## Datový model

- `users` — id, email (unique), password_hash, created_at.
- `subjects` — slug, title, weight (1–7 → římská číslice), part_kind (`karta`|`okruh`).
- `cards` — subject_id, number, slug (`karta-1`|`okruh-3`); unique(subject, number).
- `questions` — katalog: card_id, block (`A`..`H` u karet, NULL u okruhu),
  number (v bloku/okruhu), ordinal (v kartě), qid (`A1`), code (`VII/A/1`),
  text, elsewhere_id (odkaz na myslivecke-zkousky.cz), reference_md (původní
  vzorová odpověď, jen ke čtení); unique(card, block, number).
  **„Typ A/B/C" = block.**
- `user_questions` — per-user stav: user_id, question_id, hard (bool),
  answer_md (nullable), answered_at, updated_at; unique(user, question).
  Chybí řádek = neoznačeno a nezodpovězeno. Stav vyplněnosti = má answer_md.

## Pořadí stavby (atomické bloky)

1. **Datová vrstva + import katalogu** ← *tento balík*
   `app/config.py`, `app/models.py`, `app/importer.py`. Ověření `--dry-run`.
2. **Auth + skeleton** — login/registrace (z Dominia), base template, login page
   s README blurbem, session middleware, `/dashboard` stub.
3. **Dashboard + prohlížeč otázek** — statistiky (podle typu A/B/C, stavu
   vyplněnosti, počet těžkých) + procházení po předmětech/kartách.
4. **Editor odpovědi + značka „těžká"** — formulář na otázce, uložení do
   `user_questions`, toggle hard, pohled „jen těžké".
5. **Tisk** — `/print?scope=block:A|subject:VII|card:{id}` s print CSS.
6. **Deploy** — `deploy.sh`, systemd unit, nginx server blok, certbot.

## Spuštění (vývoj)

```
python -m venv .venv
.venv\Scripts\Activate.ps1          # PowerShell
pip install -r requirements.txt
python -m app.importer --dry-run    # jen statistiky, bez DB
python -m app.importer              # naplní DB (dle DATABASE_URL)
```
