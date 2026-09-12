"""Přihlášení, otevřená registrace, odhlášení. CSRF + jednoduchý per-IP lockout."""
from __future__ import annotations

import time as _t

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import (
    current_user, get_csrf_token, get_db, hash_password, login_session,
    logout_session, make_reset_token, needs_rehash, reset_token_user,
    validate_csrf, verify_password,
)
from ..config import settings
from ..mailer import send_email
from ..models import User
from ..templates import templates

APP = "MyslivecZkouška"

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
def login_form(request: Request, reset: int = 0):
    if current_user(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request, "login.html",
        {"csrf_token": get_csrf_token(request), "error": None, "reset": bool(reset)},
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


@router.get("/forgot")
def forgot_form(request: Request):
    if current_user(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request, "forgot.html", {"csrf_token": get_csrf_token(request), "error": None, "sent": False}
    )


@router.post("/forgot")
def forgot_submit(request: Request, email: str = Form(...), csrf_token: str = Form(""),
                  db: Session = Depends(get_db)):
    if not validate_csrf(request, csrf_token):
        return templates.TemplateResponse(
            request, "forgot.html",
            {"csrf_token": get_csrf_token(request),
             "error": "Vypršela platnost formuláře, zkuste to prosím znovu.", "sent": False},
            status_code=400)
    entered = email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == entered).first()
    if user:
        link = f"{settings.site_base_url}/reset/{make_reset_token(user)}"
        body = (f"Dobrý den,\n\npro nastavení nového hesla k účtu na {APP} otevřete odkaz:\n"
                f"{link}\n\nOdkaz platí 1 hodinu. Pokud jste o reset nežádal(a), e-mail ignorujte.\n")
        html = (f"<p>Dobrý den,</p><p>pro nastavení nového hesla k účtu na <strong>{APP}</strong> "
                f'klikněte na odkaz:</p><p><a href="{link}">Nastavit nové heslo</a></p>'
                "<p>Odkaz platí 1 hodinu. Pokud jste o reset nežádal(a), e-mail ignorujte.</p>")
        try:
            send_email(user.email, f"{APP} — reset hesla", body, html=html)
        except Exception:
            pass  # neutrální odpověď níže, detaily neprozrazujeme
    # vždy stejná odpověď — neprozrazuje, jestli e-mail existuje
    return templates.TemplateResponse(
        request, "forgot.html",
        {"csrf_token": get_csrf_token(request), "error": None, "sent": True})


@router.get("/reset/{token}")
def reset_form(token: str, request: Request, db: Session = Depends(get_db)):
    user = reset_token_user(db, token)
    return templates.TemplateResponse(
        request, "reset.html",
        {"token": token, "valid": bool(user), "csrf_token": get_csrf_token(request), "error": None})


@router.post("/reset/{token}")
def reset_submit(token: str, request: Request, password: str = Form(...),
                 password2: str = Form(...), csrf_token: str = Form(""),
                 db: Session = Depends(get_db)):
    def page(valid, error=None, code=400):
        return templates.TemplateResponse(
            request, "reset.html",
            {"token": token, "valid": valid, "csrf_token": get_csrf_token(request), "error": error},
            status_code=code)
    if not validate_csrf(request, csrf_token):
        return page(True, "Vypršela platnost formuláře, zkuste to prosím znovu.")
    user = reset_token_user(db, token)
    if not user:
        return page(False)
    if password != password2:
        return page(True, "Hesla se neshodují.")
    if len(password) < 8:
        return page(True, "Heslo musí mít aspoň 8 znaků.")
    user.password_hash = hash_password(password)
    db.commit()
    return RedirectResponse("/login?reset=1", status_code=303)


@router.get("/logout")
def logout(request: Request):
    logout_session(request)
    return RedirectResponse("/login", status_code=303)
