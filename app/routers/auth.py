"""Přihlášení, otevřená registrace, odhlášení. CSRF + jednoduchý per-IP lockout."""
from __future__ import annotations

import time as _t

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import (
    current_user, get_csrf_token, get_db, hash_password, login_session,
    logout_session, needs_rehash, validate_csrf, verify_password,
)
from ..models import User
from ..templates import templates

router = APIRouter()

# per-IP lockout (in-memory) — 8 neúspěchů / 15 min
_FAILS: dict[str, list[float]] = {}
_MAX, _WINDOW = 8, 900


def _ip(request: Request) -> str:
    return (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "?"))


def _locked(ip: str) -> bool:
    now = _t.time()
    fails = [t for t in _FAILS.get(ip, []) if now - t < _WINDOW]
    _FAILS[ip] = fails
    return len(fails) >= _MAX


def _fail(ip: str) -> None:
    _FAILS.setdefault(ip, []).append(_t.time())


def _ok(ip: str) -> None:
    _FAILS.pop(ip, None)


@router.get("/login")
def login_form(request: Request):
    if current_user(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request, "login.html", {"csrf_token": get_csrf_token(request), "error": None}
    )


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    def fail(msg: str, code: int = 401):
        return templates.TemplateResponse(
            request, "login.html", {"csrf_token": get_csrf_token(request), "error": msg},
            status_code=code,
        )

    if not validate_csrf(request, csrf_token):
        return fail("Vypršela platnost formuláře, zkuste to prosím znovu.")

    ip = _ip(request)
    if _locked(ip):
        return fail("Příliš mnoho neúspěšných pokusů. Zkuste to prosím za 15 minut.")

    entered = email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == entered).first()
    if not user or not verify_password(password, user.password_hash):
        _fail(ip)
        return fail("Neplatný e-mail nebo heslo.")

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()

    _ok(ip)
    login_session(request, user)
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/register")
def register_form(request: Request):
    if current_user(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request, "register.html", {"csrf_token": get_csrf_token(request), "error": None}
    )


@router.post("/register")
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    def fail(msg: str):
        return templates.TemplateResponse(
            request, "register.html", {"csrf_token": get_csrf_token(request), "error": msg},
            status_code=400,
        )

    if not validate_csrf(request, csrf_token):
        return fail("Vypršela platnost formuláře, zkuste to prosím znovu.")

    entered = email.strip().lower()
    if "@" not in entered or "." not in entered.split("@")[-1]:
        return fail("Zadejte prosím platný e-mail.")
    if password != password2:
        return fail("Hesla se neshodují.")
    if len(password) < 8:
        return fail("Heslo musí mít aspoň 8 znaků.")
    if db.query(User).filter(func.lower(User.email) == entered).first():
        return fail("Účet s tímto e-mailem už existuje.")

    user = User(email=entered, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    login_session(request, user)
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/logout")
def logout(request: Request):
    logout_session(request)
    return RedirectResponse("/login", status_code=303)
