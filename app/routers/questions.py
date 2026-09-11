"""Prohlížeč otázek a editor odpovědí.

- katalog (Subject/Card/Question) je sdílený a jen ke čtení
- Question.reference_md = původní odpověď = MASTER (jen ke čtení, nikdy se nepřepíše)
- UserQuestion.answer_md = tvoje vlastní odpověď (per-user)
- UserQuestion.hard = tvoje značka „těžká" (per-user)
"""
from __future__ import annotations

import datetime as dt

import markdown as md
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import current_user, get_csrf_token, get_db, validate_csrf
from ..models import Card, Question, Subject, UserQuestion
from ..templates import templates

router = APIRouter()


def _uq(db: Session, uid: int, qid: int) -> UserQuestion | None:
    return db.query(UserQuestion).filter_by(user_id=uid, question_id=qid).one_or_none()


def _render_md(text: str | None) -> str:
    return md.markdown(text, extensions=["extra", "sane_lists"]) if text else ""


@router.get("/questions")
def questions_index(request: Request, db: Session = Depends(get_db)):
    uid = current_user(request)["id"]
    subjects = db.query(Subject).order_by(Subject.weight).all()
    stats: dict[int, dict] = {}
    for s in subjects:
        qids = [q.id for c in s.cards for q in c.questions]
        answered = hard = 0
        if qids:
            answered = (db.query(func.count(UserQuestion.id)).filter(
                UserQuestion.user_id == uid, UserQuestion.question_id.in_(qids),
                UserQuestion.answer_md.isnot(None), UserQuestion.answer_md != "").scalar() or 0)
            hard = (db.query(func.count(UserQuestion.id)).filter(
                UserQuestion.user_id == uid, UserQuestion.question_id.in_(qids),
                UserQuestion.hard.is_(True)).scalar() or 0)
        stats[s.id] = {"total": len(qids), "answered": answered, "hard": hard}
    return templates.TemplateResponse(request, "questions.html", {"subjects": subjects, "stats": stats})


@router.get("/questions/subject/{slug}")
def subject_view(slug: str, request: Request, db: Session = Depends(get_db)):
    uid = current_user(request)["id"]
    s = db.query(Subject).filter_by(slug=slug).one_or_none()
    if not s:
        return RedirectResponse("/questions", status_code=303)
    state = {r.question_id: r for r in db.query(UserQuestion).filter_by(user_id=uid).all()}
    return templates.TemplateResponse(
        request, "subject.html",
        {"subject": s, "state": state, "csrf_token": get_csrf_token(request)},
    )


@router.get("/questions/{qid}")
def question_view(qid: int, request: Request, saved: int = 0, db: Session = Depends(get_db)):
    uid = current_user(request)["id"]
    q = db.get(Question, qid)
    if not q:
        return RedirectResponse("/questions", status_code=303)
    card: Card = q.card
    sibs = card.questions  # seřazeno dle ordinal
    idx = next((i for i, x in enumerate(sibs) if x.id == qid), None)
    prev_q = sibs[idx - 1] if idx not in (None, 0) else None
    next_q = sibs[idx + 1] if idx is not None and idx + 1 < len(sibs) else None
    uq = _uq(db, uid, qid)
    return templates.TemplateResponse(
        request, "question.html",
        {
            "q": q, "card": card, "subject": card.subject,
            "answer_md": (uq.answer_md if uq and uq.answer_md else ""),
            "hard": bool(uq and uq.hard),
            "master_html": _render_md(q.reference_md),
            "master_raw": q.reference_md or "",
            "has_master": bool(q.reference_md),
            "prev_q": prev_q, "next_q": next_q,
            "csrf_token": get_csrf_token(request), "saved": bool(saved),
        },
    )


@router.post("/questions/{qid}")
def question_save(
    qid: int, request: Request,
    answer_md: str = Form(""), hard: str = Form(None), csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    uid = current_user(request)["id"]
    if not validate_csrf(request, csrf_token):
        return RedirectResponse(f"/questions/{qid}", status_code=303)
    q = db.get(Question, qid)
    if not q:
        return RedirectResponse("/questions", status_code=303)
    uq = _uq(db, uid, qid)
    if uq is None:
        uq = UserQuestion(user_id=uid, question_id=qid)
        db.add(uq)
    uq.answer_md = answer_md.strip() or None
    uq.hard = hard is not None
    uq.answered_at = dt.datetime.utcnow() if uq.answer_md else None
    db.commit()
    return RedirectResponse(f"/questions/{qid}?saved=1", status_code=303)


@router.post("/questions/{qid}/hard")
def toggle_hard(
    qid: int, request: Request,
    csrf_token: str = Form(""), back: str = Form("/questions"),
    db: Session = Depends(get_db),
):
    uid = current_user(request)["id"]
    if not validate_csrf(request, csrf_token):
        return RedirectResponse(back, status_code=303)
    uq = _uq(db, uid, qid)
    if uq is None:
        uq = UserQuestion(user_id=uid, question_id=qid, hard=True)
        db.add(uq)
    else:
        uq.hard = not uq.hard
    db.commit()
    return RedirectResponse(back, status_code=303)


@router.get("/hard")
def hard_list(request: Request, db: Session = Depends(get_db)):
    uid = current_user(request)["id"]
    rows = (
        db.query(Question)
        .join(UserQuestion, UserQuestion.question_id == Question.id)
        .filter(UserQuestion.user_id == uid, UserQuestion.hard.is_(True))
        .all()
    )
    rows.sort(key=lambda q: (q.card.subject.weight, q.card.number, q.ordinal))
    answered = {r.question_id: bool(r.answer_md)
                for r in db.query(UserQuestion).filter_by(user_id=uid).all()}
    return templates.TemplateResponse(
        request, "hard.html", {"questions": rows, "answered": answered}
    )
