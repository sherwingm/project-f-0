"""Shadow check before switching the live data source from Kotak to Upstox (2026-10-19, the user's request).

While Kotak feeds the live server and an Upstox Analytics Token is set, every COMPARE_EVERY seconds of a session
(09:20-15:25 IST) this prices the same F&O contracts on both, back to back, through each provider's quote_many:

    the paper account's open positions, and for COMPARE_STOCKS stocks of the scan (alphabetical, rotating) the near
    future plus the call and the put nearest the live stock price.

Per contract it records last price, best bid / ask and their quantities, volume, OI, average traded price and the
quote time on each side. The day's file data/provider_compare/<YYYY-MM-DD>.json (mirrored to paper-state) holds a
summary per round, the day's running totals and the 20 largest last-price gaps; GET /api/data/compare serves it.
Nothing here trades or changes the live feed: it only reads, about 2 calls per provider per round.

What to look for before switching: last prices within a tick or two (they are fetched ~1 s apart), the same best
bid / ask most of the time, OI equal, volume in the same unit (ratio ~1: rules.walk_live divides volume by the lot
size), and Upstox's quote times not behind Kotak's.
"""
from __future__ import annotations

import json
import logging
import statistics
import threading
import time as _time
from datetime import datetime, time
from pathlib import Path

from server import sessions
from server.broker import tradingsymbol

log = logging.getLogger("provider_compare")

COMPARE_EVERY = 300
COMPARE_STOCKS = 10
WINDOW = (time(9, 20), time(15, 25))
TOP = 20


def _row(q: dict | None) -> dict | None:
    if not q:
        return None
    d = q.get("depth") or {}
    bid, ask = (d.get("bid") or [(None, None)])[0], (d.get("ask") or [(None, None)])[0]
    return {"ltp": q.get("last_price"), "bid": bid[0], "bid_qty": bid[1], "ask": ask[0], "ask_qty": ask[1],
            "volume": q.get("volume"), "oi": q.get("open_interest"), "atp": q.get("atp"), "ts": q.get("timestamp")}


def _secs(ts: str | None) -> float | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").timestamp() if ts else None
    except (TypeError, ValueError):
        return None


def compare_round(pairs: dict[str, tuple[dict | None, dict | None]]) -> dict:
    """One round's comparison of {contract: (kotak quote row, upstox quote row)} -> summary and per-contract gaps."""
    both = {c: (k, u) for c, (k, u) in pairs.items() if k and u}
    gaps, same_bid, same_ask, vol_ratio, oi_same, lag = [], [], [], [], [], []
    for c, (k, u) in both.items():
        if k["ltp"] and u["ltp"]:
            gaps.append((abs(u["ltp"] - k["ltp"]) / k["ltp"] * 100, c, k["ltp"], u["ltp"]))
        if k["bid"] and u["bid"]:
            same_bid.append(k["bid"] == u["bid"])
        if k["ask"] and u["ask"]:
            same_ask.append(k["ask"] == u["ask"])
        if k["volume"] and u["volume"]:
            vol_ratio.append(u["volume"] / k["volume"])
        if k["oi"] is not None and u["oi"] is not None:
            oi_same.append(k["oi"] == u["oi"])
        tk, tu = _secs(k["ts"]), _secs(u["ts"])
        if tk and tu:
            lag.append(tu - tk)
    share = lambda xs: round(100 * sum(xs) / len(xs), 1) if xs else None            # noqa: E731
    med = lambda xs, n=3: round(statistics.median(xs), n) if xs else None             # noqa: E731
    return {"contracts": len(pairs), "on_both": len(both),
            "missing_kotak": sorted(c for c, (k, u) in pairs.items() if not k),
            "missing_upstox": sorted(c for c, (k, u) in pairs.items() if not u),
            "ltp_gap_pct_median": med([g[0] for g in gaps]), "ltp_gap_pct_max": round(max(g[0] for g in gaps), 3) if gaps else None,
            "same_best_bid_pct": share(same_bid), "same_best_ask_pct": share(same_ask),
            "volume_ratio_median": med(vol_ratio), "oi_same_pct": share(oi_same),
            "upstox_minus_kotak_quote_time_s_median": med(lag, 1),
            "gaps": [{"contract": c, "gap_pct": round(g, 3), "kotak": kl, "upstox": ul} for g, c, kl, ul in gaps]}


class ProviderCompare:
    def __init__(self, data_dir: Path, kotak, upstox, contracts):
        """contracts(i) -> [tradingsymbol, ...] for round i (open positions + rotating futures / near-money options)."""
        self.dir = Path(data_dir) / "provider_compare"
        self.kotak, self.upstox, self.contracts = kotak, upstox, contracts
        self.status = {"enabled": True, "last_round": None, "error": None}
        self._i = 0
        self._stop = threading.Event()

    def path(self, day: str) -> Path:
        return self.dir / f"{day}.json"

    def load(self, day: str) -> dict:
        p = self.path(day)
        try:
            return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        except ValueError:
            return {}

    def run_once(self, now: datetime) -> dict:
        names = sorted(set(self.contracts(self._i)))
        self._i += 1
        k = self.kotak.quote_many(names)
        u = self.upstox.quote_many(names)
        pairs = {n: (_row(k.get(n)), _row(u.get(n))) for n in names}
        r = compare_round(pairs)
        day = now.date().isoformat()
        doc = self.load(day) or {"date": day, "rounds": [], "top_gaps": []}
        gaps = r.pop("gaps")
        doc["rounds"].append({"at": now.strftime("%H:%M:%S"), **r})
        top = doc["top_gaps"] + [{**g, "at": now.strftime("%H:%M")} for g in gaps]
        doc["top_gaps"] = sorted(top, key=lambda g: -g["gap_pct"])[:TOP]
        rs = doc["rounds"]
        vals = lambda f: [x[f] for x in rs if x.get(f) is not None]                    # noqa: E731
        med = lambda xs: round(statistics.median(xs), 3) if xs else None               # noqa: E731
        doc["day"] = {"rounds": len(rs), "contract_quotes": sum(x["on_both"] for x in rs),
                      "ltp_gap_pct_median": med(vals("ltp_gap_pct_median")),
                      "same_best_bid_pct": med(vals("same_best_bid_pct")), "same_best_ask_pct": med(vals("same_best_ask_pct")),
                      "volume_ratio_median": med(vals("volume_ratio_median")), "oi_same_pct": med(vals("oi_same_pct")),
                      "upstox_minus_kotak_quote_time_s_median": med(vals("upstox_minus_kotak_quote_time_s_median"))}
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path(day).write_text(json.dumps(doc, indent=1), encoding="utf-8")
        self.status.update(last_round=now.isoformat(timespec="seconds"), error=None)
        return doc

    def run(self) -> None:
        while not self._stop.wait(5):
            now = datetime.now(sessions.IST)
            if not (sessions.is_session(now.date()) and WINDOW[0] <= now.time() <= WINDOW[1]):
                continue
            last = self.status["last_round"]
            if last and _time.time() - datetime.fromisoformat(last).timestamp() < COMPARE_EVERY:
                continue
            try:
                self.run_once(now)
            except Exception as exc:  # noqa: BLE001 - a shadow check must never touch the live server
                self.status.update(error=str(exc)[:300], last_round=now.isoformat(timespec="seconds"))
                log.warning("provider compare: %s", exc)

    def start(self) -> None:
        threading.Thread(target=self.run, name="provider-compare", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()


def contract_picker(ledger, stocks: dict, fut_symbols, spot, upstox):
    """contracts(i): open option positions, plus for COMPARE_STOCKS stocks (rotating through the scan) the near
    future and the near-month call and put whose strike is nearest the live price (from Upstox's instrument master)."""
    syms = sorted(stocks)

    def pick(i: int) -> list[str]:
        out = [p["tradingsymbol"] for p in (ledger.state.get("positions") if ledger else []) or []]
        if not syms:
            return out
        futs = fut_symbols() or {}
        upstox.load_instruments()
        for j in range(COMPARE_STOCKS):
            s = syms[(i * COMPARE_STOCKS + j) % len(syms)]
            f = futs.get(s)
            f = f[0] if isinstance(f, list) and f else f
            if f:
                out.append(f)
            px = spot(s)
            near = [(v["expiry"], k[4]) for k, v in upstox._fo.items() if k[0] == s and k[1] == "CE" and k[4] is not None]
            if not px or not near:
                continue
            exp = min(e for e, _ in near)
            strike = min((k for e, k in near if e == exp), key=lambda k: (abs(k - px), k))
            out += [tradingsymbol(s, "CE", exp, strike), tradingsymbol(s, "PE", exp, strike)]
        return out

    return pick
