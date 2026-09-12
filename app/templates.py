"""Sdílená Jinja2 instance — routery ji importují odsud (jako core/templates.py
v Dominiu)."""
from fastapi.templating import Jinja2Templates

from .config import BASE_DIR

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["APP_NAME"] = "MyslivecZkouška"
