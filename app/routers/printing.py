"""Tiskové sestavy — JEN tvoje vlastní odpovědi (žádný vzor), a jen otázky,
které máš vyplněné. Tisk přes prohlížeč: Ctrl+P → Uložit jako PDF.

Režimy: /print/subject/{slug}, /print/card/{id}, /print/hard, rozcestník /print.
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


def _answered_map(db: Session, uid: int, ids: list[int]) -> dict[int, UserQuestion]:
    if not ids:
        return {}
    return {r.question_id: r for r in db.query(UserQuestion).filter(
        UserQuestion.user_id == uid,
        UserQuestion.question_id.in_(ids),
        UserQuestion.answer_md.isnot(None),
        UserQuestion.answer_md != "").all()}


def _rows(db: Session, uid: int, questions: list[Question]) -> list[dict]:
    """Jen otázky, na které má uživatel vlastní odpověď; vrací jen tu odpověď."""
    st = _answered_map(db, uid, [q.id for q in questions])
    out = []
    for q in questions:
        r = st.get(q.id)
        if not r:
            continue
        out.append({"code": q.code, "qid": q.qid, "text": q.text,
                    "answer_html": _render_md(r.answer_md)})
    return out


def _label(subject: Subject, card: Card) -> str:
    kind = "Okruh" if subject.part_kind == "okruh" else "Karta"
    return f"{subject.roman} · {kind} {card.number}"


def _render(request: Request, doc_title: str, groups: list[dict]):
    groups = [g for g in groups if g["rows"]]          # zahoď prázdné skupiny
    return templates.TemplateResponse(
        request, "print.html", {"doc_title": doc_title, "groups": groups})


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
    return _render(request, f"{_label(c.subject, c)} — {c.subject.title}",
                   [{"heading": _label(c.subject, c), "rows": _rows(db, uid, c.questions)}])


@router.get("/print/subject/{slug}")
def print_subject(slug: str, request: Request, db: Session = Depends(get_db)):
    uid = current_user(request)["id"]
    s = db.query(Subject).filter_by(slug=slug).one_or_none()
    if not s:
        return RedirectResponse("/print", status_code=303)
    groups = [{"heading": _label(s, c), "rows": _rows(db, uid, c.questions)} for c in s.cards]
    return _render(request, f"{s.roman} · {s.title}", groups)


@router.get("/print/hard")
def print_hard(request: Request, db: Session = Depends(get_db)):
    uid = current_user(request)["id"]
    rows = (db.query(Question)
            .join(UserQuestion, UserQuestion.question_id == Question.id)
            .filter(UserQuestion.user_id == uid, UserQuestion.hard.is_(True),
                    UserQuestion.answer_md.isnot(None), UserQuestion.answer_md != "")
            .all())
    rows.sort(key=lambda q: (q.card.subject.weight, q.card.number, q.ordinal))
    st = _answered_map(db, uid, [q.id for q in rows])
    groups, cur = [], None
    for q in rows:
        s = q.card.subject
        if cur is None or cur["_sid"] != s.id:
            cur = {"_sid": s.id, "heading": f"{s.roman} · {s.title}", "rows": []}
            groups.append(cur)
        cur["rows"].append({"code": q.code, "qid": q.qid, "text": q.text,
                            "answer_html": _render_md(st[q.id].answer_md)})
    return _render(request, "Těžké otázky — tvoje odpovědi", groups)
