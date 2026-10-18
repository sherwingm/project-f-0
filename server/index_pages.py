"""/index (and /index/...): the index-trading page (templates/index_trading.html), same layout and styling as /s2.
Read-only: it shows data coverage, recorder health, the expired-token probes, the next expiries and an empty Pods
section. Nothing on it can place an order."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from server.config import settings

router = APIRouter()
TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index_trading.html"


@router.get("/index", response_class=HTMLResponse)
@router.get("/index/{section:path}", response_class=HTMLResponse)
def index_page(section: str = ""):
    html = TEMPLATE.read_text(encoding="utf-8")
    return html.replace("/*__SERVER__*/{}", json.dumps(settings.public()))
