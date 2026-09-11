"""Přehled po přihlášení. Zatím souhrn (celkem otázek, podle typu, tvých
odpovědí, těžkých) + seznam předmětů. Plný dashboard s prohlížečem přidá blok #3."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import current_user, get_db
from ..models import Question, Subject, UserQuestion
from ..templates import templates

router = APIRouter()


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    u = current_user(request)
    if not u:
        return RedirectResponse("/login", status_code=303)

    total = db.query(func.count(Question.id)).scalar() or 0
    by_block = dict(
        db.query(Question.block, func.count(Question.id)).group_by(Question.block).all()
    )
    types = {(k or "—"): v for k, v in sorted(by_block.items(), key=lambda x: (x[0] or "~"))}

    answered = (
        db.query(func.count(UserQuestion.id))
        .filter(
            UserQuestion.user_id == u["id"],
            UserQuestion.answer_md.isnot(None),
            UserQuestion.answer_md != "",
        )
        .scalar()
        or 0
    )
    hard = (
        db.query(func.count(UserQuestion.id))
        .filter(UserQuestion.user_id == u["id"], UserQuestion.hard.is_(True))
        .scalar()
        or 0
    )

    subjects = db.query(Subject).order_by(Subject.weight).all()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": u,
            "total": total,
            "answered": answered,
            "hard": hard,
            "types": types,
            "subjects": subjects,
        },
    )
