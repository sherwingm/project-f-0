"""S3 G1 / G1-F live paper trading (strategies/S3_G1_put_overnight.md; the user, 2026-11-04: "make this live in the
website ... the same as how the s1 do"). Paper only: no order is sent anywhere, and the S1 paper account
(server/paper.py) is not touched; G1 keeps its own ledger, data/g1_ledger.json.

Every second (the fast loop in server/app.py, after the NIFTY recorder) from the Upstox stream:
    NIFTY 50 last price -> 1-minute bars (close = the minute's last print), India VIX last print, and the best bid /
    ask of the NIFTY puts the recorder already subscribes (ATM +/- 10 strikes, two weekly expiries).
Rules (the page; the same as scanner/s3_g1_forward.py, which stays the record for the verdict):
    opening range 09:15-09:29; the first 1-minute close outside it from 09:30 to 13:00; only a close below the low
    trades; buy 1 lot of the ATM put (strike nearest the entry minute's close) of the nearest weekly expiry after
    today, at the last ask of the minute after the signal minute; sell at the bid when it is <= 50 % of the price
    paid (any second, both days), else (from 2026-11-06, the user) at the best bid at the first quote of the next
    session's 15:29 minute (the close). Before that date the exit was the last bid of the next 09:16 minute.
    G1-F takes the same trade only when, at the signal, the day-1 opening gap < +0.3 %, the range width is not in
    0.5 %-0.8 % and India VIX < 17. One position serves both tracks; each trade says whether G1-F counts it.
    G1-F is the MAIN track from 2026-11-06 (the user: "make the g1-f as main"): shown first on the page, and the alert
    says whether G1-F counts the trade. The ledger still records every G1 trade, so G1's own gate is unchanged.
A restart in the session rebuilds today's minute bars from the recorder's own file (data/candles_1s_index/<day>.jsonl).
"""
from __future__ import annotations

import json
import logging
import math
import os
import threading
import time as time_mod
from datetime import date, datetime, time, timedelta
from pathlib import Path

from server import alerts, sessions
from server import charges as ch
from server import g1_score

log =logging.getLogger("g1")
IST = sessions.IST
SPOT_KEY, VIX_KEY = "NSE_INDEX|Nifty 50", "NSE_INDEX|India VIX"
STEP, LOT, STOP = 50, 65, 0.50
OR_FROM, OR_TO, LAST_SIGNAL, EXIT_MIN = time(9, 15), time(9, 30), time(13, 0), time(9, 16)
CLOSE_MIN = time(15, 29)                    # G1: the next session's last minute (the close)
GAP_MAX, WIDTH_SKIP, VIX_MAX = 0.3, (0.5, 0.8), 17.0
QUOTE_AGE = 60.0
EPOCH = "2026-11-05 G1 live paper"
PAGE = "strategies/S3_G1_put_overnight.md"
SCORE_KEYS = ("score", "score_pct", "score_band", "score_items", "score_missing", "score_pctile", "score_avg_pct", "score_inputs")


def _best(s: dict | None) -> tuple[float | None, float | None]:
    """(best bid, best ask) of a stream state."""
    dp = (s or {}).get("depth") or []
    bid = max((p for p, q, _, _ in dp if p and q), default=None)
    ask = min((p for _, _, p, q in dp if p and q), default=None)
    return bid, ask


def _ltp(s: dict | None) -> float | None:
    v = ((s or {}).get("ltpc") or {}).get("ltp")
    return float(v) if v else None


def g1f_check(gap: float | None, width: float, vix: float | None) -> str:
    """"" when G1-F takes the trade, else the reasons it skips (the page, "Second track")."""
    why = []
    if gap is None:
        why.append("no previous close")
    elif gap >= GAP_MAX:
        why.append(f"day-1 gap {gap:+.2f} % ≥ +{GAP_MAX} %")
    if WIDTH_SKIP[0] <= width < WIDTH_SKIP[1]:
        why.append(f"range width {width:.2f} % in {WIDTH_SKIP[0]}-{WIDTH_SKIP[1]} %")
    if vix is None:
        why.append("no VIX")
    elif vix >= VIX_MAX:
        why.append(f"VIX {vix:.2f} ≥ {VIX_MAX:.0f}")
    return "; ".join(why)


def median(x: list[float]) -> float | None:
    if not x:
        return None
    s, n = sorted(x), len(x)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def t_stat(x: list[float]) -> float | None:
    n = len(x)
    if n < 3:
        return None
    m = sum(x) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))
    return m / (sd / math.sqrt(n)) if sd > 0 else None


class G1Trader:
    """One rule-trading paper ledger. A subclass (server/nt_live.py, Near Tighty) changes the class attributes and
    the two hooks `entry_skip` / `entry_note` / `tracks`; the signal, entry, stop and exit stay exactly G1's."""
    NAME, LEDGER, EPOCH, PAGE = "G1", "g1_ledger.json", EPOCH, PAGE
    SCORE = True              # the 0-7 breakout score (record only); Near Tighty is not scored here
    HOLD_TO_CLOSE = True      # G1 / G1-F (2026-11-06, the user): hold to the next session's close; a subclass may say False
    # the market of the run; Near Tighty on SENSEX (server/nt_live.py) changes these and `subscribe`
    INDEX, SPOT, SPOT_LABEL, STEP, KEYS = "NIFTY", SPOT_KEY, "NIFTY 50", STEP, "_nifty"

    def __init__(self, stream, upstox, data_dir, lot: int = LOT):
        self.stream, self.upstox, self.lot = stream, upstox, lot
        self.dir = Path(data_dir)
        self.file = self.dir / self.LEDGER
        self.lock = threading.Lock()
        self.state = self._load()
        self.day: date | None = None
        self.bars: dict[time, dict] = {}            # minute -> {o, h, l, c}
        self.vix: list[tuple[datetime, float]] = []
        self.asks: dict[float, tuple[datetime, float]] = {}     # strike -> (seen at, ask) during the entry minute
        self.last_bid: tuple[datetime, float] | None = None
        self.prev_close: float | None = None
        self._pos_saved: datetime | None = None            # when the open position's marks were last saved
        self._closes: tuple | None = None                  # (day, daily closes or None, fetched at): for the score

    # ------------------------------------------------------------ ledger
    def _load(self) -> dict:
        try:
            st = json.loads(self.file.read_text(encoding="utf-8"))
            if st.get("epoch") == self.EPOCH:
                return st
        except (OSError, ValueError):
            pass
        return {"epoch": self.EPOCH, "open": None, "trades": [], "days": {}}

    def _save(self) -> None:
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=1, default=str), encoding="utf-8")
        os.replace(tmp, self.file)

    def _today(self) -> dict:
        return self.state["days"].setdefault(self.day.isoformat(), {"status": "waiting for 09:15"})

    # ------------------------------------------------------------ inputs
    def _nifty_keys(self) -> dict:
        return getattr(self.upstox, self.KEYS, None) or {}

    def subscribe(self, now: datetime) -> None:
        """Hook: ask the stream for this market's keys (NIFTY's come from the index recorder; SENSEX subscribes its own)."""

    def expiry_after(self, today: date) -> str | None:
        exps = sorted({e for e, typ, _ in self._nifty_keys() if typ == "PE" and e > today.isoformat()})
        return exps[0] if exps else None

    def _key(self, expiry: str, strike: float) -> str | None:
        return self._nifty_keys().get((expiry, "PE", float(strike)))

    def _seed(self, now: datetime) -> None:
        """Today's NIFTY 50 minute bars from the recorder's file, after a restart in the session (a market the recorder
        does not write, SENSEX, has no file: a restart inside the session loses that day's opening range)."""
        f = self.dir / "candles_1s_index" / f"{now.date()}.jsonl"
        if not f.exists():
            return
        try:
            for line in f.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                if r.get("ts") == self.SPOT_LABEL and r.get("c"):
                    hh, mm, _ = map(int, r["t"].split(":"))
                    self._bar(time(hh, mm), float(r["c"]))
                elif r.get("ts") == "INDIA VIX" and r.get("c"):
                    hh, mm, ss = map(int, r["t"].split(":"))
                    self.vix.append((datetime.combine(now.date(), time(hh, mm, ss), IST), float(r["c"])))
        except (OSError, ValueError, KeyError) as exc:
            log.warning("g1: could not seed today's bars from the recorder file (%s)", exc)

    def _bar(self, m: time, px: float) -> None:
        b = self.bars.get(m)
        if b is None:
            self.bars[m] = {"o": px, "h": px, "l": px, "c": px}
        else:
            b["h"], b["l"], b["c"] = max(b["h"], px), min(b["l"], px), px

    # ------------------------------------------------------------ the loop
    def tick(self, now: datetime) -> None:
        with self.lock:
            if now.date() != self.day:
                self.day, self.bars, self.vix, self.asks, self.last_bid = now.date(), {}, [], {}, None
                self.prev_close = None
                if sessions.is_index_session(now.date()) and now.time() > OR_FROM:
                    self._seed(now)
            if sessions.is_index_session(now.date()) and time(9, 0) <= now.time() <= time(15, 31):
                self.subscribe(now)                       # before 09:15, so the first minute's prices are there
            if not sessions.is_index_session(now.date()) or not time(9, 15) <= now.time() <= time(15, 30):
                return
            sp = self.stream.get(self.SPOT)
            px = _ltp(sp)
            if px:
                self._bar(now.time().replace(second=0, microsecond=0), px)
                cp = ((sp or {}).get("ltpc") or {}).get("cp")
                if cp and self.prev_close is None:
                    self.prev_close = float(cp)
            vx = _ltp(self.stream.get(VIX_KEY))
            if vx:
                self.vix.append((now, vx))
            self._manage_open(now)
            self._signal(now)

    def _signal(self, now: datetime) -> None:
        st = self._today()
        phase = st.get("phase", "range")
        if phase == "range" and now.time() >= OR_TO:
            rng = [b for m, b in self.bars.items() if OR_FROM <= m < OR_TO]
            if not rng:
                st.update(phase="done", status=f"no {self.INDEX} prices for the opening range: no trade")
                self._save()
                return
            st.update(phase="scan", hi=max(b["h"] for b in rng), lo=min(b["l"] for b in rng),
                      open=self.bars[min(m for m in self.bars if m >= OR_FROM)]["o"],
                      status="watching for the first breakout (09:30-13:00)")
            self._save()
            phase = "scan"
        if phase == "scan":
            hi, lo = st["hi"], st["lo"]
            done = sorted(m for m in self.bars if OR_TO <= m <= LAST_SIGNAL
                          and datetime.combine(self.day, m, IST) + timedelta(minutes=1) <= now)
            for m in done:
                c = self.bars[m]["c"]
                if c > hi:
                    st.update(phase="done", status=f"first breakout up at {m:%H:%M} ({c:,.2f} > {hi:,.2f}): no trade today")
                    self._save()
                    return
                if c < lo:
                    ent = (datetime.combine(self.day, m, IST) + timedelta(minutes=1)).time()
                    width = (hi - lo) / lo * 100
                    gap = (st["open"] / self.prev_close - 1) * 100 if self.prev_close else None
                    end = datetime.combine(self.day, m, IST) + timedelta(minutes=1)
                    vix = next((v for t, v in reversed(self.vix) if t < end), None)
                    st.update(phase="entry", signal=f"{m:%H:%M}", signal_close=c, entry=f"{ent:%H:%M}",
                              gap_pct=None if gap is None else round(gap, 3), width_pct=round(width, 3), vix=vix,
                              g1f_skip=g1f_check(gap, width, vix), **self._score(lo, c, m, width, gap, vix),
                              status=f"downside breakout at {m:%H:%M} ({c:,.2f} < {lo:,.2f}): buying at {ent:%H:%M}")
                    self._save()
                    phase = "entry"
                    break
            else:
                if now.time() > time(13, 1):
                    st.update(phase="done", status="no breakout by 13:00: no trade today")
                    self._save()
                return
        if phase == "entry":
            self._entry(now, st)

    def _entry(self, now: datetime, st: dict) -> None:
        ent = datetime.combine(self.day, time.fromisoformat(st["entry"]), IST)
        exp = self.expiry_after(self.day)
        if exp is None:
            st.update(phase="done", status=f"no {self.INDEX} expiry after today in the instrument list: no trade")
            self._save()
            return
        why = self.entry_skip(self.day, exp)
        if why:
            st.update(phase="done", status=why)
            self._save()
            return
        if ent <= now < ent + timedelta(minutes=1):            # the entry minute: keep every strike's last ask
            spot = (self.bars.get(ent.time()) or {}).get("c")
            if spot:
                atm = round(spot / self.STEP) * self.STEP
                for k in (atm - 2 * self.STEP, atm - self.STEP, atm, atm + self.STEP, atm + 2 * self.STEP):
                    key = self._key(exp, k)
                    _, ask = _best(self.stream.get(key)) if key else (None, None)
                    if ask:
                        self.asks[float(k)] = (now, ask)
            return
        if now < ent:
            return
        if self.state.get("open"):
            st.update(phase="done", status=f"the previous {self.NAME} position is still open: no new trade")
            self._save()
            return
        spot = (self.bars.get(ent.time()) or {}).get("c")
        k = float(round(spot / self.STEP) * self.STEP) if spot else None
        seen = self.asks.get(k) if k is not None else None
        if seen is None or (ent + timedelta(minutes=1) - seen[0]).total_seconds() > QUOTE_AGE:
            st.update(phase="done", status=f"no ask for the {k:.0f} PE in the {st['entry']} minute: no trade" if k
                      else f"no {self.INDEX} price in the {st['entry']} minute: no trade")
            self._save()
            return
        paid = seen[1]
        fees = ch.leg("PE", "BUY", self.lot, paid)["total"]
        self.state["open"] = {"day": self.day.isoformat(), "signal": st["signal"], "entry": st["entry"],
                              "bought_at": seen[0].isoformat(timespec="seconds"), "expiry": exp, "strike": k,
                              "key": self._key(exp, k), "paid": paid, "qty": self.lot, "entry_fees": round(fees, 2),
                              "spot": spot, "g1f_skip": st["g1f_skip"], "gap_pct": st["gap_pct"],
                              "width_pct": st["width_pct"], "vix": st["vix"], "mark": paid, "max_bid": paid,
                              **{k: st[k] for k in SCORE_KEYS if k in st}}
        st.update(phase="done", status=f"bought {self.INDEX} {exp} {k:.0f} PE at ₹{paid:.2f} (ask)"
                  + self.entry_note(st))
        self._save()
        alerts.send(f"🟢 {self.NAME} paper: bought {self.INDEX} {exp} {k:.0f} PE × {self.lot} at ₹{paid:.2f} (signal {st['signal']})"
                    + self.entry_note(st) + self._score_text(st),
                    key=f"{self.NAME.lower()}-open-{self.day}", every=3600)

    def _manage_open(self, now: datetime) -> None:
        pos = self.state.get("open")
        if not pos:
            return
        if pos.get("key"):
            self.stream.want([pos["key"]])                     # stays subscribed overnight whatever NIFTY does
        bid, _ = _best(self.stream.get(pos["key"])) if pos.get("key") else (None, None)
        if bid:
            pos["mark"] = bid
            pos["max_bid"] = max(pos.get("max_bid") or 0, bid)
            pos["marked_at"] = now.isoformat(timespec="seconds")
            if self._pos_saved is None or (now - self._pos_saved).total_seconds() > 30:   # keep mark / best bid on disk
                self._pos_saved = now                                                   # (a restart must not lose the max up)
                self._save()
            if bid <= pos["paid"] * (1 - STOP):
                self._close(pos, bid, now, "stop")
                return
        if now.date().isoformat() <= pos["day"]:
            return
        if self.HOLD_TO_CLOSE:
            pos.setdefault("hold_day", now.date().isoformat())
            if now.date().isoformat() > pos["hold_day"]:           # the close was missed (server down): first bid
                if bid:
                    self._close(pos, bid, now, "next close missed (server was down): sold at the first bid")
                return
            if now.time() >= CLOSE_MIN and bid:
                self._close(pos, bid, now, "next close")
            return
        m = now.time()
        if m < EXIT_MIN:
            return
        if m < time(9, 17):                                    # the exit minute: keep its last bid
            if bid:
                self.last_bid = (now, bid)
            return
        if self.last_bid is not None:
            self._close(pos, self.last_bid[1], self.last_bid[0], "next open")
        elif bid:
            self._close(pos, bid, now, "next open (late: no bid in the 09:16 minute)")

    def _close(self, pos: dict, sold: float, at: datetime, why: str) -> None:
        fees = pos["entry_fees"] + ch.leg("PE", "SELL", pos["qty"], sold)["total"]
        gross = (sold - pos["paid"]) * pos["qty"]
        net = gross - fees
        t = {**{k: v for k, v in pos.items() if k not in ("mark", "marked_at")}, "sold": sold,
             "sold_at": at.isoformat(timespec="seconds"), "reason": why, "gross_rs": round(gross, 2),
             "fees_rs": round(fees, 2), "net_rs": round(net, 2),
             "net_pct": round(net / (pos["paid"] * pos["qty"]) * 100, 2),
             "max_up_pct": round((pos["max_bid"] / pos["paid"] - 1) * 100, 1)}
        self.state["trades"].append(t)
        self.state["open"] = None
        self.last_bid = None
        self._save()
        alerts.send(f"{'🔴' if net < 0 else '✅'} {self.NAME} paper: sold {self.INDEX} {pos['expiry']} {pos['strike']:.0f} PE at ₹{sold:.2f} "
                    f"({why}), net ₹{net:,.0f} ({t['net_pct']:+.1f} %), max up {t['max_up_pct']:+.0f} %"
                    + (f"; {g1_score.line(t)}" if t.get("score") is not None else ""), key=f"{self.NAME.lower()}-close-{pos['day']}", every=3600)

    # ------------------------------------------------------------ score (record only)
    def _score(self, lo: float, close: float, m: time, width: float, gap: float | None, vix: float | None) -> dict:
        """The 0-7 breakout score of this signal (g1_research/SCORE_PREREG.md). Record only: nothing here gates a trade."""
        if not self.SCORE:
            return {}
        try:
            now = time_mod.monotonic()
            if self._closes is None or self._closes[0] != self.day or (self._closes[1] is None and now - self._closes[2] > 60):
                self._closes = (self.day, g1_score.daily_closes(self.upstox, self.day), now)
            f = g1_score.features(lo, close, m, width, gap, vix, self._closes[1])
            before = [d["score"] for k, d in sorted(self.state["days"].items()) if k < self.day.isoformat() and "score" in d]
            return g1_score.stamp(f, before)
        except Exception as exc:  # noqa: BLE001 - a record must never stop the trade
            log.warning("g1 score failed (%s)", exc)
            return {}

    def _score_text(self, st: dict) -> str:
        return "; " + g1_score.line(st) if "score" in st else ""

    # ------------------------------------------------------------ hooks
    def entry_skip(self, day: date, expiry: str) -> str:
        """"" to trade; else why this strategy takes no trade today (G1: never skips here)."""
        return ""

    def entry_note(self, st: dict) -> str:
        return "; G1-F counts it" if not st["g1f_skip"] else f"; G1-F skips ({st['g1f_skip']})"

    def tracks(self, trades: list) -> list:
        return [("G1-F (main)", [t for t in trades if not t.get("g1f_skip")]), ("G1 (baseline)", trades)]

    # ------------------------------------------------------------ views
    def view(self) -> dict:
        with self.lock:
            st = json.loads(json.dumps(self.state, default=str))
        trades = st["trades"]
        out = {"page": self.PAGE, "epoch": self.EPOCH, "lot": self.lot, "open": st["open"], "trades": trades[::-1],
               "today": st["days"].get(datetime.now(IST).date().isoformat()), "tracks": []}
        if st["open"]:
            o = st["open"]
            exit_fee = ch.leg("PE", "SELL", o["qty"], o["mark"])["total"] if o.get("mark") else 0
            o["unrealised_rs"] = round((o["mark"] - o["paid"]) * o["qty"] - o["entry_fees"] - exit_fee, 2) if o.get("mark") else None
        for name, sel in self.tracks(trades):
            x = [t["net_pct"] for t in sel]
            mu = [t["max_up_pct"] for t in sel if t.get("max_up_pct") is not None]
            out["tracks"].append({
                "pod": name, "trades": len(sel), "gate_at": 30,
                "max_up_mean": sum(mu) / len(mu) if mu else None, "max_up_median": median(mu),     # the lead measure
                "max_up_100": sum(v >= 100 for v in mu) / len(mu) if mu else None,
                "won": sum(v > 0 for v in x) / len(x) if x else None,
                "mean_pct": sum(x) / len(x) if x else None,
                "median_pct": median(x),
                "t": t_stat(x), "total_rs": round(sum(t["net_rs"] for t in sel), 2),
                "status": "forward paper · verdict at 30 trades",
                "bands": g1_score.bands(sel) if self.SCORE else []})
        if self.SCORE:
            out["score_meta"] = g1_score.meta()
        return out
