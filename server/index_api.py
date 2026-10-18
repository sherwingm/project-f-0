"""/api/index/... : read-only data for the index-trading page (INDEX_DATA_PLAN.md §8). No order path.

The Render instance has no persistent disk and does not redeploy on data commits, so the small JSON summaries
(data/index/*.json on main, written by the GitHub Actions) are read from GitHub's raw URL next to SCAN_URL, falling
back to the local copy. Cached for 5 minutes.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests
from fastapi import APIRouter

from server.config import settings

router = APIRouter(prefix="/api/index")
ROOT = Path(__file__).resolve().parents[1]
FILES = ("status.json", "coverage.json", "expiries_next.json", "probe_expired.json", "reconcile.json", "chain_latest.json")
_cache: dict[str, tuple[float, object]] = {}
TTL = 300.0


def _raw_base() -> str | None:
    u = settings.scan_url
    return u.rsplit("/data/", 1)[0] + "/data/index/" if u and "/data/" in u else None


def read(name: str):
    hit = _cache.get(name)
    if hit and time.monotonic() - hit[0] < TTL:
        return hit[1]
    val = None
    base = _raw_base()
    if base:
        try:
            r = requests.get(base + name, timeout=15)
            if r.status_code == 200:
                val = r.json()
        except (requests.RequestException, ValueError):
            val = None
    if val is None:
        try:
            val = json.loads((ROOT / "data" / "index" / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            val = None
    _cache[name] = (time.monotonic(), val)
    return val


@router.get("/status")
def status():
    return {"status": read("status.json"), "coverage": read("coverage.json")}


@router.get("/expiries")
def expiries():
    return read("expiries_next.json")


@router.get("/probe")
def probe():
    return read("probe_expired.json") or []


@router.get("/reconcile")
def reconcile():
    return read("reconcile.json")


@router.get("/chain")
def chain():
    return read("chain_latest.json")


@router.get("/positions")
def positions():
    return {"pods": [], "positions": [], "note": "no index pods yet: data layer only (INDEX_DATA_PLAN.md)"}


@router.get("/results")
def results():
    return {"pods": [], "note": "no index pods yet: strategy results plug in here"}
