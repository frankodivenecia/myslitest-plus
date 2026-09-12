"""Tiskové sestavy (otázka + tvoje odpověď; když chybí, doplní se vzor).
Tisk přes prohlížeč: stránka je uzpůsobená pro Ctrl+P → Uložit jako PDF.

Řezy: /print/card/{id}, /print/subject/{slug}, /print/block/{A|B|C}, rozcestník /print.
"""
from __future__ import annotations

import markdown as md
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth import current_user, get_db
from ..models import Card, Question, Subject, UserQuestion
from ..templates import templates

router = APIRouter()


def _render_md(text: str | None) -> str:
    return md.markdown(text, extensions=["extra", "sane_lists"]) if text else ""


def _items(db: Session, uid: int, questions: list[Question]) -> list[dict]:
    if not questions:
        return []
    ids = [q.id for q in questions]
    st = {r.question_id: r for r in db.query(UserQuestion).filter(
        UserQuestion.user_id == uid, UserQuestion.question_id.in_(ids)).all()}
    out = []
    for q in questions:
        r = st.get(q.id)
        if r and r.answer_md:
            answer_html, is_master = _render_md(r.answer_md), False
        elif q.reference_md:
            answer_html, is_master = _render_md(q.reference_md), True
        else:
            answer_html, is_master = "", False
        out.append({"code": q.code, "qid": q.qid, "text": q.text,
                    "answer_html": answer_html, "is_master": is_master})
    return out


def _label(subject: Subject, card: Card) -> str:
    kind = "Okruh" if subject.part_kind == "okruh" else "Karta"
    return f"{subject.roman} · {kind} {card.number}"


@router.get("/print")
def print_index(request: Request, db: Session = Depends(get_db)):
    subjects = db.query(Subject).order_by(Subject.weight).all()
    return templates.TemplateResponse(request, "print_index.html", {"subjects": subjects})


@router.get("/print/card/{card_id}")
def print_card(card_id: int, request: Request, db: Session = Depends(get_db)):
    uid = current_user(request)["id"]
    c = db.get(Card, card_id)
    if not c:
        return RedirectResponse("/print", status_code=303)
    groups = [{"heading": _label(c.subject, c), "rows": _items(db, uid, c.questions)}]
    return templates.TemplateResponse(request, "print.html", {
        "doc_title": _label(c.subject, c) + " — " + c.subject.title, "groups": groups})


@router.get("/print/subject/{slug}")
def print_subject(slug: str, request: Request, db: Session = Depends(get_db)):
    uid = current_user(request)["id"]
    s = db.query(Subject).filter_by(slug=slug).one_or_none()
    if not s:
        return RedirectResponse("/print", status_code=303)
    groups = [{"heading": _label(s, c), "rows": _items(db, uid, c.questions)} for c in s.cards]
    return templates.TemplateResponse(request, "print.html", {
        "doc_title": f"{s.roman} · {s.title}", "groups": groups})


@router.get("/print/block/{letter}")
def print_block(letter: str, request: Request, db: Session = Depends(get_db)):
    uid = current_user(request)["id"]
    letter = letter.upper()[:1]
    subjects = db.query(Subject).order_by(Subject.weight).all()
    groups = []
    for s in subjects:
        qs = [q for c in s.cards for q in c.questions if (q.block or "") == letter]
        qs.sort(key=lambda q: (q.card.number, q.ordinal))
        if qs:
            groups.append({"heading": f"{s.roman} · {s.title}", "rows": _items(db, uid, qs)})
    return templates.TemplateResponse(request, "print.html", {
        "doc_title": f"Všechny otázky typu {letter}", "groups": groups})
