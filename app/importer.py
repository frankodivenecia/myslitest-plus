"""Import pevného katalogu otázek z původního Hugo obsahu (content/predmet/**)
do DB.

Struktura obsahu:
- content/predmet/<slug>/_index.md ....... front matter: title, weight, part
- content/predmet/<slug>/<karta-N>/_index.md  front matter: elsewhere (mapa),
  tělo: `## nadpis bloku` + číslované otázky; položka může být odkaz [text](aN/…)
- content/predmet/<slug>/<karta-N>/<qid>.md   vzorová odpověď (prázdný = žádná)

Bloky jsou dané pořadím `##` sekcí → písmena A, B, C… (u part=okruh se otázky
zploští do jedné řady bez písmen). „Typ A/B/C" = block.

Použití:
    python -m app.importer --dry-run          # jen statistiky (bez DB, jen pyyaml)
    python -m app.importer                     # naplní DB dle DATABASE_URL
    python -m app.importer --content PATH      # jiná složka content/
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import settings

ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
LETTERS = "ABCDEFGH"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)
HEAD_RE = re.compile(r"^##\s+(.*\S)\s*$")
ITEM_RE = re.compile(r"^\d+\.\s+(.*\S)\s*$")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
TRAIL_NUM_RE = re.compile(r"(\d+)$")


@dataclass
class Q:
    block: str | None
    number: int
    ordinal: int
    qid: str
    code: str
    text: str
    elsewhere_id: int | None
    reference_md: str | None


@dataclass
class C:
    number: int
    slug: str
    questions: list[Q] = field(default_factory=list)


@dataclass
class S:
    slug: str
    title: str
    weight: int
    part_kind: str
    cards: list[C] = field(default_factory=list)


def split_front_matter(text: str) -> tuple[dict, str]:
    m = FM_RE.match(text)
    if m:
        data = yaml.safe_load(m.group(1)) or {}
        return (data if isinstance(data, dict) else {}), m.group(2)
    return {}, text


def parse_card_body(body: str) -> list[tuple[str, list[str]]]:
    """Vrátí [(nadpis_bloku, [text_otázky, …]), …] v pořadí sekcí."""
    blocks: list[tuple[str, list[str]]] = []
    cur: list[str] | None = None
    for line in body.splitlines():
        h = HEAD_RE.match(line)
        if h:
            cur = []
            blocks.append((h.group(1), cur))
            continue
        it = ITEM_RE.match(line)
        if it and cur is not None:
            blocks[-1][1].append(LINK_RE.sub(r"\1", it.group(1)).strip())
    return blocks


def read_reference(card_dir: Path, qid: str) -> str | None:
    f = card_dir / f"{qid.lower()}.md"
    if not f.exists():
        return None
    _, body = split_front_matter(f.read_text(encoding="utf-8"))
    body = body.strip()
    return body or None


def _card_number(p: Path) -> int:
    m = TRAIL_NUM_RE.search(p.name)
    return int(m.group(1)) if m else 0


def load_catalog(content_dir: Path) -> list[S]:
    predmet = content_dir / "predmet"
    if not predmet.is_dir():
        raise SystemExit(f"Nenašel jsem {predmet} — zkontroluj --content / CONTENT_DIR.")

    subjects: list[S] = []
    for subj_dir in sorted(p for p in predmet.iterdir() if p.is_dir()):
        fm, _ = split_front_matter((subj_dir / "_index.md").read_text(encoding="utf-8"))
        weight = int(fm.get("weight", 0) or 0)
        part_kind = str(fm.get("part", "karta"))
        roman = ROMAN[weight] if 0 < weight < len(ROMAN) else str(weight)
        subject = S(subj_dir.name, str(fm.get("title", subj_dir.name)), weight, part_kind)

        for card_dir in sorted((p for p in subj_dir.iterdir() if p.is_dir()), key=_card_number):
            num = _card_number(card_dir)
            fmc, body = split_front_matter((card_dir / "_index.md").read_text(encoding="utf-8"))
            elsewhere = fmc.get("elsewhere") or {}
            card = C(num, card_dir.name)
            ordinal = 0

            if part_kind == "okruh":
                n = 0
                for _heading, items in parse_card_body(body):
                    for text in items:
                        n += 1
                        ordinal += 1
                        qid = str(n)
                        code = f"{roman}/O{num}/{n}"
                        card.questions.append(
                            Q(None, n, ordinal, qid, code, text, None, read_reference(card_dir, qid))
                        )
            else:
                for bi, (_heading, items) in enumerate(parse_card_body(body)):
                    letter = LETTERS[bi] if bi < len(LETTERS) else f"X{bi}"
                    base = elsewhere.get(letter)
                    for j, text in enumerate(items, start=1):
                        ordinal += 1
                        qid = f"{letter}{j}"
                        code = f"{roman}/{letter}/{num}"
                        el = (int(base) + j - 1) if base is not None else None
                        card.questions.append(
                            Q(letter, j, ordinal, qid, code, text, el, read_reference(card_dir, qid))
                        )

            subject.cards.append(card)
        subjects.append(subject)

    subjects.sort(key=lambda s: s.weight)
    return subjects


def print_stats(subjects: list[S]) -> None:
    tot_q = tot_c = with_ref = 0
    by_type: Counter[str] = Counter()
    print("Katalog otázek — přehled")
    print("=" * 64)
    for s in subjects:
        roman = ROMAN[s.weight] if 0 < s.weight < len(ROMAN) else str(s.weight)
        nq = sum(len(c.questions) for c in s.cards)
        types = Counter(q.block or "—" for c in s.cards for q in c.questions)
        tstr = ", ".join(f"{k}:{v}" for k, v in sorted(types.items()))
        print(f"{roman:>4}  {s.title:<42} [{s.part_kind}]  {len(s.cards)} karet, {nq} ot.  ({tstr})")
        tot_c += len(s.cards)
        tot_q += nq
        by_type.update(types)
        with_ref += sum(1 for c in s.cards for q in c.questions if q.reference_md)
    print("=" * 64)
    print(f"Celkem: {len(subjects)} předmětů, {tot_c} karet, {tot_q} otázek")
    print("Podle typu: " + ", ".join(f"{k}:{v}" for k, v in sorted(by_type.items())))
    print(f"Se vzorovou odpovědí: {with_ref}/{tot_q}")


def seed(subjects: list[S]) -> None:
    # Import až tady, aby --dry-run nepotřeboval SQLAlchemy ani DB driver.
    from .models import Base, Card, Question, Subject, SessionLocal, engine

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for s in subjects:
            subj = db.query(Subject).filter_by(slug=s.slug).one_or_none()
            if subj is None:
                subj = Subject(slug=s.slug)
                db.add(subj)
            subj.title, subj.weight, subj.part_kind = s.title, s.weight, s.part_kind
            db.flush()

            for c in s.cards:
                card = db.query(Card).filter_by(subject_id=subj.id, number=c.number).one_or_none()
                if card is None:
                    card = Card(subject_id=subj.id, number=c.number)
                    db.add(card)
                card.slug = c.slug
                db.flush()

                for q in c.questions:
                    row = (
                        db.query(Question)
                        .filter_by(card_id=card.id, block=q.block, number=q.number)
                        .one_or_none()
                    )
                    if row is None:
                        row = Question(card_id=card.id, block=q.block, number=q.number)
                        db.add(row)
                    row.ordinal = q.ordinal
                    row.qid = q.qid
                    row.code = q.code
                    row.text = q.text
                    row.elsewhere_id = q.elsewhere_id
                    row.reference_md = q.reference_md
        db.commit()


def main() -> None:
    ap = argparse.ArgumentParser(description="Import katalogu otázek z Hugo obsahu do DB.")
    ap.add_argument("--dry-run", action="store_true", help="jen vypiš statistiky, nezapisuj do DB")
    ap.add_argument("--content", default=None, help="cesta ke složce content/")
    args = ap.parse_args()

    content_dir = Path(args.content) if args.content else settings.content_dir
    subjects = load_catalog(content_dir)
    print_stats(subjects)

    if args.dry_run:
        print("\n(dry-run — do DB se nic nezapsalo)")
    else:
        seed(subjects)
        print(f"\nZapsáno do DB: {settings.database_url}")


if __name__ == "__main__":
    main()
