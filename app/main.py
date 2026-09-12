"""FastAPI aplikace MyslíTest.

Vrstvy middleware (přidané pořadí = od vnitřní k vnější):
  1) require_login  — guard, přesměruje nepřihlášené na /login
  2) security_headers
  3) SessionMiddleware — přidán poslední → běží první → session je k dispozici v guardu
"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .auth import current_user, is_public_path
from .config import BASE_DIR, settings
from .models import Base, engine
from .routers import auth as auth_router
from .routers import dashboard as dashboard_router
from .routers import printing as printing_router
from .routers import questions as questions_router

app = FastAPI(title="MyslivecZkouška")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.middleware("http")
async def require_login(request: Request, call_next):
    path = request.url.path
    if path == "/" or is_public_path(path):
        return await call_next(request)
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return resp


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true",
)


@app.on_event("startup")
def _startup():
    # vytvoří tabulky, které ještě nejsou (users, user_questions, katalog);
    # katalog naplní `python -m app.importer`
    Base.metadata.create_all(bind=engine)


app.include_router(auth_router.router)
app.include_router(dashboard_router.router)
app.include_router(questions_router.router)
app.include_router(printing_router.router)


@app.get("/")
def root(request: Request):
    return RedirectResponse("/dashboard" if current_user(request) else "/login", status_code=303)


@app.get("/health")
def health():
    return {"status": "ok"}
