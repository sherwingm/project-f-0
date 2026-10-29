"""The index-options paper ledger: multi-leg positions, quote-based fills, held and after-exit observations.

Conventions (match server/peak.py for S1, applied to a whole position):
    - a paper BUY fills at each leg's best ASK, a paper SELL at each leg's best BID: never at the last trade or a mid;
    - a leg whose quote has no ask (entry) or no bid (exit), or whose last trade is from before today's 09:15 open,
      is not filled: the entry is rejected, or the exit waits (exit_pending) until every leg has a live bid;
    - the position's sellable value at an observation = the sum over legs of bid x qty, and only when EVERY leg has a
      bid in that same poll (otherwise the observation counts as missing);
    - peak / low are the highest / lowest OBSERVED sellable value from the first poll after the entry through the poll
      that triggered the exit; equal values keep the earliest time; max_gap_s is the longest gap between two polls;
    - after the exit the legs are still recorded for POST_EXIT_MINUTES (phase "after_exit"); that follow-up never
      touches the held peak or any P&L.
Store: <data_dir>/index_paper/state.json (open + closed, atomic write) and observations/<date>.jsonl (one row per leg
per bid/ask change). IDs: IX-<POD>-<YYYYMMDD>-<NNN>, unique per pod and day, never reused.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path

from server import charges as ch
from server.peak import IST, entry_quote, not_traded_today

POST_EXIT_MINUTES = 60
STORE_DIR = "index_paper"


class IndexPaperRejected(ValueError):
    """An entry that cannot be filled from the quotes given (no ask, stale quote, bad legs, pod off)."""


def _best(quote: dict | None, side: str) -> tuple[float | None, int | None]:
    d = (quote or {}).get("depth") or {}
    lvl = (d.get(side) or [(None, None)])[0]
    px, qty = (lvl[0], lvl[1]) if len(lvl) >= 2 else (lvl[0] if lvl else None, None)
    return (float(px) if px and px > 0 else None), qty


def leg_symbol(leg: dict) -> str:
    return leg["symbol"]


class IndexPaperLedger:
    def __init__(self, data_dir: Path | str):
        self.dir = Path(data_dir) / STORE_DIR
        self.path = self.dir / "state.json"
        self._lock = threading.RLock()
        self._last_obs: dict[str, tuple] = {}
        self.state = self._load()

    # ---- persistence
    def _load(self) -> dict:
        try:
            s = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            s = {}
        s.setdefault("open", [])
        s.setdefault("closed", [])
        s.setdefault("seq", {})
        s.setdefault("rejected", [])
        return s

    def save(self) -> None:
        with self._lock:
            self.dir.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self.state, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)

    def new_id(self, pod: str, now: datetime) -> str:
        key = f"{pod}:{now.astimezone(IST):%Y%m%d}"
        n = self.state["seq"].get(key, 0) + 1
        self.state["seq"][key] = n
        return f"IX-{pod}-{now.astimezone(IST):%Y%m%d}-{n:03d}"

    # ---- entry
    def open(self, pod: str, legs: list[dict], quotes: dict, now: datetime, reason: str = "",
             exit_plan: dict | None = None) -> dict:
        """Buy every leg at its best ask. legs: [{"symbol", "underlying", "expiry", "strike", "opt" CE/PE, "qty"}].
        Rejected (IndexPaperRejected, recorded in state["rejected"]) unless every leg has a live ask."""
        with self._lock:
            problems = []
            if not legs:
                problems.append("no legs")
            for lg in legs:
                if lg.get("opt") not in ("CE", "PE") or not lg.get("qty") or lg["qty"] <= 0:
                    problems.append(f"{lg.get('symbol')}: bad leg")
                    continue
                q = quotes.get(lg["symbol"])
                if not q:
                    problems.append(f"{lg['symbol']}: no quote")
                elif not_traded_today(q, now):
                    problems.append(f"{lg['symbol']}: last trade before today's open")
                elif _best(q, "ask")[0] is None:
                    problems.append(f"{lg['symbol']}: no ask")
            if problems:
                self.state["rejected"].append({"pod": pod, "at": now.isoformat(timespec="seconds"), "reason": reason,
                                               "problems": problems})
                self.save()
                raise IndexPaperRejected("; ".join(problems))
            out_legs, debit, fees = [], 0.0, 0.0
            for lg in legs:
                q = quotes[lg["symbol"]]
                ask, _ = _best(q, "ask")
                f = ch.leg(lg["opt"], "BUY", lg["qty"], ask)["total"]
                out_legs.append({**lg, "entry_px": ask, "entry_fees": f, "entry_quote": entry_quote(q, now)})
                debit += ask * lg["qty"]
                fees += f
            pos = {"id": self.new_id(pod, now), "pod": pod, "status": "open", "reason": reason,
                   "opened_at": now.isoformat(timespec="seconds"), "legs": out_legs, "debit_rs": round(debit, 2),
                   "entry_fees": round(fees, 2), "exit_plan": exit_plan or {},
                   "held": {"first": None, "peak": None, "low": None, "last": None, "n": 0, "missing": 0, "max_gap_s": None}}
            self.state["open"].append(pos)
            self.save()
            return pos

    # ---- observations
    def _log(self, pos: dict, lg: dict, q: dict | None, now: datetime, phase: str) -> None:
        b, bq = _best(q, "bid")
        a, aq = _best(q, "ask")
        key = (b, bq, a, aq)
        lk = f"{pos['id']}:{lg['symbol']}:{phase}"
        if self._last_obs.get(lk) == key:
            return
        self._last_obs[lk] = key
        row = {"id": pos["id"], "pod": pos["pod"], "t": now.isoformat(timespec="seconds"), "symbol": lg["symbol"],
               "bid": b, "bid_qty": bq, "ask": a, "ask_qty": aq, "ltp": (q or {}).get("last_price"),
               "ltt": (q or {}).get("timestamp"), "spot": (q or {}).get("underlying"),
               "src": (q or {}).get("source"), "phase": phase}
        d = self.dir / "observations"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / f"{now.astimezone(IST).date().isoformat()}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")

    @staticmethod
    def sellable(pos: dict, quotes: dict) -> tuple[float | None, dict | None]:
        """(sum of bid x qty over the legs, {symbol: bid}), or (None, None) if any leg has no bid in these quotes."""
        tot, bids = 0.0, {}
        for lg in pos["legs"]:
            b, _ = _best(quotes.get(lg["symbol"]), "bid")
            if b is None:
                return None, None
            tot += b * lg["qty"]
            bids[lg["symbol"]] = b
        return round(tot, 2), bids

    @staticmethod
    def _track(h: dict, value: float | None, now: datetime, bids: dict | None = None) -> None:
        if value is None:
            h["missing"] += 1
            return
        at = now.isoformat(timespec="seconds")
        if h["last"] is not None:
            gap = (now - datetime.fromisoformat(h["last"]["at"])).total_seconds()
            h["max_gap_s"] = max(h.get("max_gap_s") or 0.0, round(gap, 1))
        pt = {"value": value, "at": at, "bids": bids}
        if h["first"] is None:
            h["first"] = pt
        if h["peak"] is None or value > h["peak"]["value"]:
            h["peak"] = pt
        if h["low"] is None or value < h["low"]["value"]:
            h["low"] = pt
        h["last"] = pt
        h["n"] += 1

    def observe(self, quotes: dict, now: datetime) -> list[dict]:
        """One poll for every open position: log the legs, update the held peak / low. Returns the open positions."""
        with self._lock:
            for pos in self.state["open"]:
                for lg in pos["legs"]:
                    self._log(pos, lg, quotes.get(lg["symbol"]), now, "held")
                v, b = self.sellable(pos, quotes)
                self._track(pos["held"], v, now, b)
            self.save()
            return list(self.state["open"])

    # ---- exit
    def close(self, pos_id: str, quotes: dict, now: datetime, reason: str) -> dict | None:
        """Sell every leg at its best bid. If any leg has no live bid the position stays open with exit_pending set
        (no invented fill) and None is returned."""
        with self._lock:
            pos = next((p for p in self.state["open"] if p["id"] == pos_id), None)
            if pos is None:
                raise KeyError(pos_id)
            bids = {}
            for lg in pos["legs"]:
                q = quotes.get(lg["symbol"])
                b, bq = _best(q, "bid")
                if b is None or not_traded_today(q, now):
                    pos["exit_pending"] = {"reason": reason, "since": pos.get("exit_pending", {}).get("since")
                                           or now.isoformat(timespec="seconds"), "waiting_for": lg["symbol"]}
                    self.save()
                    return None
                bids[lg["symbol"]] = (b, bq, q)
            proceeds, fees = 0.0, 0.0
            for lg in pos["legs"]:
                b, bq, q = bids[lg["symbol"]]
                f = ch.leg(lg["opt"], "SELL", lg["qty"], b)["total"]
                lg.update({"exit_px": b, "exit_fees": f, "exit_quote": entry_quote(q, now)})
                proceeds += b * lg["qty"]
                fees += f
            # the exit poll is the last held observation
            self._track(pos["held"], round(proceeds, 2), now, {s_: v[0] for s_, v in bids.items()})
            net = proceeds - pos["debit_rs"] - pos["entry_fees"] - fees
            pos.update({"status": "closed", "closed_at": now.isoformat(timespec="seconds"), "exit_reason": reason,
                        "proceeds_rs": round(proceeds, 2), "exit_fees": round(fees, 2), "net_rs": round(net, 2),
                        "net_pct": round(net / pos["debit_rs"] * 100, 2) if pos["debit_rs"] else None,
                        "after_until": (now + timedelta(minutes=POST_EXIT_MINUTES)).isoformat(timespec="seconds"),
                        "after": {"first": None, "peak": None, "low": None, "last": None, "n": 0, "missing": 0,
                                  "max_gap_s": None}})
            pos.pop("exit_pending", None)
            pos["capture"] = capture(pos)
            self.state["open"] = [p for p in self.state["open"] if p["id"] != pos_id]
            self.state["closed"].append(pos)
            self.save()
            return pos

    def observe_after(self, quotes: dict, now: datetime) -> None:
        """The hypothetical follow-up of closed positions until after_until (never part of the held peak or P&L)."""
        with self._lock:
            for pos in self.state["closed"]:
                if not pos.get("after_until") or now > datetime.fromisoformat(pos["after_until"]):
                    continue
                for lg in pos["legs"]:
                    self._log(pos, lg, quotes.get(lg["symbol"]), now, "after_exit")
                v, b = self.sellable(pos, quotes)
                self._track(pos["after"], v, now, b)
            self.save()

    def symbols_needed(self, now: datetime) -> set[str]:
        out = {lg["symbol"] for p in self.state["open"] for lg in p["legs"]}
        for p in self.state["closed"]:
            if p.get("after_until") and now <= datetime.fromisoformat(p["after_until"]):
                out |= {lg["symbol"] for lg in p["legs"]}
        return out


def capture(pos: dict) -> dict | None:
    """Bid-based peak and drawdown of a closed position. peak_net = the net had every leg sold at the peak poll's
    bids (estimated: it assumes each leg's whole size filled at that bid); capture_pct only when peak_net > 0."""
    h = pos.get("held") or {}
    if not h.get("peak") or not pos.get("debit_rs"):
        return None
    debit, peak, low = pos["debit_rs"], h["peak"]["value"], h["low"]["value"]
    pb = h["peak"].get("bids") or {}
    peak_fees = sum(ch.leg(lg["opt"], "SELL", lg["qty"], pb[lg["symbol"]])["total"] for lg in pos["legs"])
    peak_net = round(peak - debit - pos["entry_fees"] - peak_fees, 2)
    out = {"basis": "highest observed combined best bid (all legs in the same poll), not LTP",
           "peak_value": peak, "peak_at": h["peak"]["at"], "peak_bids": pb, "low_value": low, "low_at": h["low"]["at"],
           "peak_return_pct": round((peak - debit) / debit * 100, 2), "mae_pct": round((low - debit) / debit * 100, 2),
           "peak_net": peak_net, "giveback_rs": round(peak_net - pos["net_rs"], 2),
           "polls": h.get("n", 0), "missing_polls": h.get("missing", 0), "max_gap_s": h.get("max_gap_s")}
    out["capture_pct"] = round(pos["net_rs"] / peak_net * 100, 1) if peak_net > 0 else None
    return out
