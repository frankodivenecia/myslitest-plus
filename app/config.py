"""Konfigurace přes prostředí. SQLite pro lokální vývoj, Postgres v produkci."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # dotenv je volitelný
    pass

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    # Lokálně SQLite (žádný DB server), produkce přepne přes DATABASE_URL na
    # postgresql+psycopg://user:pass@host/myslitest
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'myslitest.db'}")
    secret_key: str = os.getenv("SECRET_KEY", "dev-insecure-zmenit-v-produkci")
    content_dir: Path = Path(os.getenv("CONTENT_DIR", str(BASE_DIR / "content")))


settings = Settings()
