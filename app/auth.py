"""Session autentizace ve stylu Dominia + hashování hesel bcryptem napřímo
(bez passlibu — na Py3.14/bcrypt5 passlib padá).

Jedna role, otevřená registrace. Do session cookie jde jen minimální identita
(id + e-mail), nikdy heslo. Guard middleware v main.py pošle nepřihlášené na
/login."""
from __future__ import annotations

import base64
import hashlib
import secrets

import bcrypt
from fastapi import Request

from .models import SessionLocal, User

SESSION_USER_KEY = "user"
SESSION_CSRF_KEY = "csrf"

# Cesty dostupné bez přihlášení
PUBLIC_PREFIXES = ("/login", "/register", "/logout", "/health", "/static", "/favicon")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- hesla -----------------------------------------------------------------
def _prep(pw: str) -> bytes:
    # sha256 pre-hash → obejde 72bajtový limit bcryptu bez tichého ořezu
    return base64.b64encode(hashlib.sha256(pw.encode("utf-8")).digest())


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(_prep(pw), bcrypt.gensalt()).decode("ascii")


def verify_password(pw: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(_prep(pw), hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False


def needs_rehash(hashed: str | None) -> bool:
    # místo pro budoucí zvýšení cost; zatím jen kontrola formátu
    return not (hashed or "").startswith("$2")


# --- session ---------------------------------------------------------------
def login_session(request: Request, user: User) -> None:
    request.session[SESSION_USER_KEY] = {"id": user.id, "email": user.email}


def logout_session(request: Request) -> None:
    request.session.pop(SESSION_USER_KEY, None)
    request.session.pop(SESSION_CSRF_KEY, None)


def current_user(request: Request):
    """Vrátí dict {'id','email'} přihlášeného uživatele, nebo None."""
    return request.session.get(SESSION_USER_KEY)


def is_public_path(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in PUBLIC_PREFIXES)


# --- CSRF ------------------------------------------------------------------
def get_csrf_token(request: Request) -> str:
    token = request.session.get(SESSION_CSRF_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[SESSION_CSRF_KEY] = token
    return token


def validate_csrf(request: Request, form_token: str) -> bool:
    expected = request.session.get(SESSION_CSRF_KEY, "")
    return bool(form_token) and bool(expected) and secrets.compare_digest(form_token, expected)
