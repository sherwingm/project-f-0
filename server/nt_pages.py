"""/near-tighty and /api/near-tighty: NT Near Tighty's own page (templates/near_tighty.html) and its paper ledger
(server/nt_live.py). Its own part of the site, apart from /index. Read-only: nothing here can place an order."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from server.config import settings

router = APIRouter()
TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "near_tighty.html"


@router.get("/near-tighty", response_class=HTMLResponse)
def near_tighty_page():
    html = TEMPLATE.read_text(encoding="utf-8")
    return html.replace("/*__SERVER__*/{}", json.dumps(settings.public()))


@router.get("/api/near-tighty")
def near_tighty_api():
    """Open position, today's status, closed trades and the 30-trade gate track."""
    from server.app import state                     # late import: the app module imports this router
    nt = getattr(state, "nt", None)
    return nt.view() if nt is not None else {"error": "Near Tighty paper is not running on this server "
                                                      "(it needs the Upstox stream)"}
