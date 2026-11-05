"""XP: NIFTY expiry-day ATM straddle forward log (expiry_research/FORWARD_TEST.md; the user, 2026-11-05: "Test do it",
"Both"). Paper only: no order is sent anywhere; own ledger data/xp_ledger.json; S1, G1 and NT are not touched.

On a NIFTY expiry day, from the Upstox stream (the NIFTY recorder already subscribes CE and PE, ATM +/- 10 strikes,
of the nearest expiries including today's):
    strike = ATM (50 steps) nearest NIFTY 50's first print from 09:15:00;
    buy 1 lot CE + 1 lot PE of today's expiry at each leg's last best ask in the 09:16 minute;
    primary exit: both bids together >= 1.20 x paid -> sell at those bids, else at the first quote from 15:15:00;
    shadow exit: the same position at the first quote from 15:15:00 (hold to 15:15), logged side by side.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import date, datetime, time
from pathlib import Path

from server import alerts, sessions
from server import charges as ch
from server.g1_live import SPOT_KEY, VIX_KEY, _best, _ltp, median, t_stat

log = logging.getLogger("xp")
IST = sessions.IST
STEP, LOT, TARGET, GATE = 50, 65, 0.20, 40
OPEN_FROM, ENTRY_MIN, EXIT_AT = time(9, 15), time(9, 16), time(15, 15)
EPOCH = "2026-11-05 XP expiry straddle forward log"
PAGE = "expiry_research/FORWARD_TEST.md"


def _fees(leg: str, side: str, qty: int, px: float) -> float:
    return ch.leg(leg, side, qty, px)["total"]


class ExpiryStraddleLogger:
    def __init__(self, stream, upstox, data_dir, lot: int = LOT):
        self.stream, self.upstox, self.lot = stream, upstox, lot
        self.dir = Path(data_dir)
        self.file = self.dir / "xp_ledger.json"
        self.lock = threading.Lock()
        self.state = self._load()
        self.day: date | None = None
        self.asks: dict[str, tuple[datetime, float]] = {}      # leg -> (seen at, ask) in the 09:16 minute
        self.ltps: dict[str, float] = {}

    # ------------------------------------------------------------ ledger
    def _load(self) -> dict:
        try:
            st = json.loads(self.file.read_text(encoding="utf-8"))
            if st.get("epoch") == EPOCH:
                return st
        except (OSError, ValueError):
            pass
        return {"epoch": EPOCH, "open": None, "trades": [], "days": {}}

    def _save(self) -> None:
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=1, default=str), encoding="utf-8")
        os.replace(tmp, self.file)

    def _today(self) -> dict:
        return self.state["days"].setdefault(self.day.isoformat(), {"status": "waiting"})

    def _keys(self) -> dict:
        return getattr(self.upstox, "_nifty", None) or {}

    def is_expiry(self, d: date) -> bool:
        return any(e == d.isoformat() for e, typ, _ in self._keys() if typ in ("CE", "PE"))

    # ------------------------------------------------------------ the loop
    def tick(self, now: datetime) -> None:
        with self.lock:
            if now.date() != self.day:
                self.day, self.asks, self.ltps = now.date(), {}, {}
            if not sessions.is_session(now.date()) or not time(9, 15) <= now.time() <= time(15, 30):
                return
            pos = self.state.get("open")
            if pos and pos["day"] != self.day.isoformat():         # cannot happen (closed at 15:15); never carry
                pos["note"] = "left open past its day (server down at 15:15): closed at the last mark"
                self._close(pos, now, final=True)
                pos = None
            if pos:
                self._manage(pos, now)
                return
            self._entry(now)

    def _entry(self, now: datetime) -> None:
        st = self._today()
        if st.get("phase") == "done":
            return
        if not self._keys():
            st["status"] = "waiting for the instrument list"
            return
        if not self.is_expiry(self.day):
            st.update(phase="done", status="not a NIFTY expiry day: no trade")
            self._save()
            return
        m = now.time()
        if "strike" not in st:
            px = _ltp(self.stream.get(SPOT_KEY))
            if not px or m < OPEN_FROM:
                return
            if m >= time(9, 17):
                st.update(phase="done", status="server was not running at 09:15-09:16: day missed")
                self._save()
                return
            cp = ((self.stream.get(SPOT_KEY) or {}).get("ltpc") or {}).get("cp")
            st.update(open_px=px, strike=float(round(px / STEP) * STEP),
                      gap_pct=round((px / float(cp) - 1) * 100, 3) if cp else None,
                      status=f"expiry day: ATM {round(px / STEP) * STEP:.0f} from the first print {px:,.2f}; buying at 09:16")
            self._save()
        k, exp = st["strike"], self.day.isoformat()
        if ENTRY_MIN <= m < time(9, 17):                            # keep each leg's last ask of the 09:16 minute
            for leg in ("CE", "PE"):
                key = self._keys().get((exp, leg, float(k)))
                s = self.stream.get(key) if key else None
                _, ask = _best(s)
                if ask:
                    self.asks[leg] = (now, ask)
                lp = _ltp(s)
                if lp:
                    self.ltps[leg] = lp
            return
        if m < time(9, 17):
            return
        miss = [leg for leg in ("CE", "PE") if leg not in self.asks]
        if miss:
            st.update(phase="done", status=f"no ask for the {k:.0f} {'/'.join(miss)} in the 09:16 minute: skipped")
            self._save()
            return
        vix = _ltp(self.stream.get(VIX_KEY))
        pos = {"day": exp, "expiry": exp, "strike": k, "qty": self.lot, "open_px": st["open_px"], "gap_pct": st["gap_pct"],
               "vix": vix, "bought_at": max(t for t, _ in self.asks.values()).isoformat(timespec="seconds"),
               "keys": {leg: self._keys().get((exp, leg, float(k))) for leg in ("CE", "PE")},
               "paid": {leg: self.asks[leg][1] for leg in ("CE", "PE")},
               "ltp_in": {leg: self.ltps.get(leg) for leg in ("CE", "PE")}}
        pos["paid_sum"] = round(pos["paid"]["CE"] + pos["paid"]["PE"], 2)
        pos["entry_fees"] = round(sum(_fees(leg, "BUY", self.lot, pos["paid"][leg]) for leg in ("CE", "PE")), 2)
        pos["mark"] = pos["max_bid"] = None
        self.state["open"] = pos
        st.update(phase="done", status=f"bought NIFTY {exp} {k:.0f} straddle at ₹{pos['paid_sum']:.2f} "
                  f"(CE {pos['paid']['CE']:.2f} + PE {pos['paid']['PE']:.2f}, asks)")
        self._save()
        alerts.send(f"🟢 XP paper log: bought NIFTY {exp} {k:.0f} straddle × {self.lot} at ₹{pos['paid_sum']:.2f}",
                    key=f"xp-open-{exp}", every=3600)

    def _manage(self, pos: dict, now: datetime) -> None:
        self.stream.want([k for k in pos["keys"].values() if k])
        bids, ltps = {}, {}
        for leg in ("CE", "PE"):
            s = self.stream.get(pos["keys"][leg]) if pos["keys"][leg] else None
            bids[leg], _ = _best(s)
            ltps[leg] = _ltp(s)
        if bids["CE"] and bids["PE"]:
            b = bids["CE"] + bids["PE"]
            pos.update(mark=round(b, 2), mark_bids=bids, marked_at=now.isoformat(timespec="seconds"))
            if pos.get("max_bid") is None or b > pos["max_bid"]:
                pos.update(max_bid=round(b, 2), max_at=now.isoformat(timespec="seconds"))
            if "target" not in pos and b >= pos["paid_sum"] * (1 + TARGET):
                pos["target"] = {"at": now.isoformat(timespec="seconds"), "bids": bids, "ltps": ltps}
                self._save()
                alerts.send(f"🎯 XP paper log: +20 % target hit at {now:%H:%M:%S}, bids ₹{b:.2f} (paid ₹{pos['paid_sum']:.2f}); "
                            "the shadow hold-to-15:15 runs on", key=f"xp-target-{pos['day']}", every=3600)
            if now.time() >= EXIT_AT:
                pos["at_1515"] = {"at": now.isoformat(timespec="seconds"), "bids": bids, "ltps": ltps}
                self._close(pos, now)
        elif now.time() >= time(15, 29):
            self._close(pos, now, final=True)

    def _result(self, pos: dict, bids: dict, ltps: dict | None, at: str, slip_in: float) -> dict:
        q = pos["qty"]
        sold = bids["CE"] + bids["PE"]
        fees = pos["entry_fees"] + sum(_fees(leg, "SELL", q, bids[leg]) for leg in ("CE", "PE"))
        net = (sold - pos["paid_sum"]) * q - fees
        out = {"at": at, "sold_sum": round(sold, 2), "net_rs": round(net, 2),
               "net_pct": round(net / (pos["paid_sum"] * q) * 100, 2)}
        li, lo = pos.get("ltp_in") or {}, ltps or {}
        if all(li.get(x) for x in ("CE", "PE")) and all(lo.get(x) for x in ("CE", "PE")):
            exit_slip = 0.02 if datetime.fromisoformat(at).time() >= time(15, 0) else 0.01
            pin = sum(li[x] * (1 + slip_in) for x in ("CE", "PE"))
            pout = sum(lo[x] * (1 - exit_slip) for x in ("CE", "PE"))
            out["ltp_slip_pct"] = round(((pout - pin) * q - fees) / (pin * q) * 100, 2)
        return out

    def _close(self, pos: dict, now: datetime, final: bool = False) -> None:
        last = {"at": pos.get("marked_at") or now.isoformat(timespec="seconds"), "bids": pos.get("mark_bids"), "ltps": None}
        h = pos.get("at_1515") or last
        t = {k: v for k, v in pos.items() if k not in ("mark", "mark_bids", "marked_at", "keys")}
        if h["bids"]:
            t["hold_1515"] = self._result(pos, h["bids"], h["ltps"], h["at"], 0.02)
            tg = pos.get("target")
            t["primary"] = self._result(pos, tg["bids"], tg["ltps"], tg["at"], 0.02) if tg else \
                {**t["hold_1515"], "note": "target not reached: sold at 15:15"}
            t["primary"]["exit"] = "+20 % target" if tg else "15:15"
        else:
            t["note"] = "no bids for the legs after entry: no result"
        if pos.get("max_bid"):
            t["max_up_pct"] = round((pos["max_bid"] / pos["paid_sum"] - 1) * 100, 1)
        self.state["trades"].append(t)
        self.state["open"] = None
        self._save()
        if t.get("primary"):
            p, hd = t["primary"], t["hold_1515"]
            alerts.send(f"{'✅' if p['net_rs'] > 0 else '🔴'} XP paper log {pos['day']} {pos['strike']:.0f} straddle: "
                        f"{p['exit']} {p['net_pct']:+.1f} % (₹{p['net_rs']:,.0f}); hold to 15:15 {hd['net_pct']:+.1f} %; "
                        f"max up {t.get('max_up_pct', 0):+.0f} %", key=f"xp-close-{pos['day']}", every=3600)

    # ------------------------------------------------------------ view
    def view(self) -> dict:
        with self.lock:
            st = json.loads(json.dumps(self.state, default=str))
        done = [t for t in st["trades"] if t.get("primary")]
        prim = [t["primary"]["net_pct"] for t in done]
        hold = [t["hold_1515"]["net_pct"] for t in done]
        diff = [a - b for a, b in zip(prim, hold)]
        ups = [t["max_up_pct"] for t in done if t.get("max_up_pct") is not None]
        o = st["open"]
        if o and o.get("mark"):
            q = o["qty"]
            exit_fee = sum(_fees(leg, "SELL", q, o["mark_bids"][leg]) for leg in ("CE", "PE"))
            o["unrealised_rs"] = round((o["mark"] - o["paid_sum"]) * q - o["entry_fees"] - exit_fee, 2)
        return {"page": PAGE, "epoch": EPOCH, "lot": self.lot, "open": o, "trades": st["trades"][::-1],
                "today": st["days"].get(datetime.now(IST).date().isoformat()),
                "summary": {"days": len(done), "gate_at": GATE,
                            "primary_mean_pct": sum(prim) / len(prim) if prim else None,
                            "primary_median_pct": median(prim), "primary_won": sum(v > 0 for v in prim) / len(prim) if prim else None,
                            "primary_t": t_stat(prim), "primary_total_rs": round(sum(t["primary"]["net_rs"] for t in done), 2),
                            "hold_mean_pct": sum(hold) / len(hold) if hold else None,
                            "paired_diff_mean": sum(diff) / len(diff) if diff else None,
                            "max_up_mean": sum(ups) / len(ups) if ups else None, "max_up_median": median(ups),
                            "max_up_100_share": sum(u >= 100 for u in ups) / len(ups) if ups else None,
                            "target_hit_share": sum(t["primary"]["exit"] != "15:15" for t in done) / len(done) if done else None},
                "tracks": [{"pod": "XP (+20 % target)", "trades": len(done), "gate_at": GATE,
                            "won": sum(v > 0 for v in prim) / len(prim) if prim else None,
                            "mean_pct": sum(prim) / len(prim) if prim else None, "median_pct": median(prim),
                            "t": t_stat(prim), "total_rs": round(sum(t["primary"]["net_rs"] for t in done), 2),
                            "status": "forward log · verdict at 40 expiry days"}]}
