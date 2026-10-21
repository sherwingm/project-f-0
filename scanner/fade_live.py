"""S1 results-day fade, paper only: the signals for the next session (strategies/S1_v10_results_day_fade_paper.md;
the exit is S1 v11's from 2026-10-21, strategies/S1_v11_fade_stop20.md).

    python -m scanner.fade_live            # nightly (daily.yml, 20:30 IST) and before the open (fade-morning.yml, 07:17 IST)

For every results filing whose day 0 (the first full session after it) is the next session: strong numbers (net
profit YoY > +10 %, QoQ > 0, revenue YoY > 0) -> buy a put; weak numbers (net profit YoY < -10 %, QoQ < 0) -> buy a
call. Writes data/forward/fade.json, which the scan carries as meta.fade; the live server's server/fade.py buys them
on day 0 between 09:15 and 15:20 and sells at the -20 % stop (from 09:16, at the best bid) or else at 15:20. The file
also carries the session's F&O ban list (`ban`), which server/rules.py uses to skip arms A / B.
"""
from __future__ import annotations

import argparse
import json
import logging
import zipfile
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import requests

from .build import ROOT
from .event_screens import num_or_none, strong, weak

log = logging.getLogger("fade_live")

STATE_PATH = ROOT / "data" / "forward" / "fade.json"
OPEN = time(9, 15)
MIN_LEFT = 2                                   # sessions after day 0 for the current monthly; fewer -> next monthly
HISTORY_MAX = 400
RULES_TEXT = ("S1 v12 results-day fade, paper only: on the first full session after a results filing, strong numbers "
              "(net profit YoY > +10 %, QoQ > 0, revenue YoY > 0) -> buy a put; weak numbers (net profit YoY < -10 %, "
              "QoQ < 0) -> buy a call. 1 lot at the live ask, Rs 600-8,000, walking away from the money from the "
              "strike nearest the live price, any time 09:15-15:20. Sold at the best bid once it is at or below "
              "0.80 x entry from 09:16 (-20 % stop); once the bid reaches 1.10 x entry a trailing stop sells at the "
              "first bid 2 % below the highest bid since; else at 15:20 the same day.")


# ---------------------------------------------------------------- pure rules
def classify(q: dict) -> str | None:
    """'PE' for strong numbers, 'CE' for weak ones, None otherwise."""
    if strong(q, 10):
        return "PE"
    if weak(q):
        return "CE"
    return None


def describe(q: dict) -> str:
    f = lambda k: "n/a" if num_or_none(q.get(k)) is None else f"{float(q[k]):+.1f} %"      # noqa: E731
    return f"net profit YoY {f('net_profit_yoy')}, QoQ {f('net_profit_qoq')}; revenue YoY {f('revenue_yoy')}"


def target_session(now: datetime, is_session) -> date:
    """The session the signals are for: today if before 09:15 on a session day, else the next session."""
    d = now.date()
    if is_session(d) and now.time() < OPEN:
        return d
    d += timedelta(days=1)
    while not is_session(d):
        d += timedelta(days=1)
    return d


def calendar(target: date, is_session, back: int = 20) -> list[str]:
    return [(target - timedelta(days=k)).isoformat() for k in range(back, -1, -1)
            if is_session(target - timedelta(days=k))]


def choose_expiry(expiries, target: date, sessions_to_expiry) -> str | None:
    from .option_engine import monthly
    ahead = [e for e in monthly(expiries) if e >= target.isoformat()]
    for e in ahead:
        if sessions_to_expiry(target, e) >= MIN_LEFT:
            return e
    return None


def day0_signals(results: list[tuple[str, str, str | None]], cal: list[str]) -> list[tuple[str, str, str | None]]:
    """The filings whose day 0 is the last date of `cal` (the target session), one per stock (the earliest)."""
    from .backtest_s1_v2 import day0_index
    out: dict[str, tuple[str, str, str | None]] = {}
    for sym, d, t in sorted(results, key=lambda r: (r[1], r[2] or "99:99")):
        i = day0_index(cal, d, t)
        if i is not None and i == len(cal) - 1 and sym not in out:
            out[sym] = (sym, d, t)
    return list(out.values())


# ---------------------------------------------------------------- shadow tag fd2 (strategies/S1_v11_fd2_shadow_track.md)
FD_FROM, FD_TO, FD_CUT, FD_CLOSE = "09:15", "14:50", -2.0, "15:29"


def _hm(t: str, add: int) -> str:
    h, m = map(int, t[:5].split(":"))
    x = h * 60 + m + add
    return f"{x // 60:02d}:{x % 60:02d}"


def _close_at(closes: dict, t: str, tol: int = 5) -> float | None:
    """The close of the minute starting at t, else the last close up to `tol` minutes before; None if none."""
    for k in range(tol + 1):
        v = closes.get(_hm(t, -k))
        if v and v > 0:
            return float(v)
    return None


def market_hours_filing(filed: str | None, filed_time: str | None, target: str, is_session=None) -> bool:
    """A results filing published 09:15-14:50 IST on a session day before the target session (day 0). A weekend or
    holiday filing is not one (as in the study)."""
    if not (filed and filed_time and filed < target and FD_FROM <= str(filed_time)[:5] <= FD_TO):
        return False
    if is_session is None:
        from server import sessions
        is_session = sessions.is_session
    return bool(is_session(date.fromisoformat(filed)))


def filing_day_move(stock: dict, nifty: dict, filed_time: str) -> dict:
    """D = the stock's % move from the close of the minute before the filing minute to the 15:29 close, minus NIFTY
    50's over the same minutes; tagged = D <= -2 % (the put's way already moved). None values when a price is
    missing."""
    pre = _hm(filed_time, -1)
    s0, s1 = _close_at(stock, pre), _close_at(stock, FD_CLOSE)
    n0, n1 = _close_at(nifty, pre), _close_at(nifty, FD_CLOSE)
    if not (s0 and s1 and n0 and n1):
        return {"market_hours": True, "D": None, "D_raw": None, "tagged": None, "error": "missing minute prices"}
    raw = (s1 / s0 - 1) * 100
    d = raw - (n1 / n0 - 1) * 100
    return {"market_hours": True, "D": round(d, 3), "D_raw": round(raw, 3), "tagged": d <= FD_CUT}


class FilingDayMoves:
    """Kotak 1-minute history of the filing day (consumer key only: GitHub secret KOTAK_CONSUMER_KEY). Any failure
    gives an 'unknown' tag; it never stops the signal run."""

    BUDGET_S = 120                                       # stop measuring after this long (the morning push waits)

    def __init__(self):
        self.k, self.eq, self.nifty, self.error, self.t0 = None, None, {}, None, None

    def _closes(self, neosymbol: str, day: str) -> dict:
        from index_data.common import candles_frame
        f = candles_frame(self.k.history(neosymbol, "1min", day, day))
        return dict(zip(f["timestamp"].dt.strftime("%H:%M"), f["close"]))

    def tag(self, sym: str, filed: str, filed_time: str) -> dict:
        import time as _time
        unknown = {"market_hours": True, "D": None, "D_raw": None, "tagged": None}
        if self.error:
            return {**unknown, "error": self.error}
        self.t0 = self.t0 or _time.monotonic()
        if _time.monotonic() - self.t0 > self.BUDGET_S:
            return {**unknown, "error": "time budget used up"}
        try:                                             # setup and the day's NIFTY: a failure here stops the run's tags
            if self.k is None:
                from index_data.common import Kotak
                from index_data.s1_trades_1m import eq_tokens
                self.k = Kotak()
                self.eq = eq_tokens(self.k)
            if filed not in self.nifty:
                self.nifty[filed] = self._closes("nse_cm|Nifty 50", filed)
        except (Exception, SystemExit) as exc:  # noqa: BLE001 - no key, no network: unknown, never fatal
            self.error = str(exc)[:120]
            log.warning("fd2 tag unavailable: %s", self.error)
            return {**unknown, "error": self.error}
        tok = self.eq.get(sym)
        if not tok:
            return {**unknown, "error": "no Kotak token"}
        try:                                             # one stock's failure leaves the others measurable
            return filing_day_move(self._closes(f"nse_cm|{tok}", filed), self.nifty[filed], filed_time)
        except Exception as exc:  # noqa: BLE001
            return {**unknown, "error": str(exc)[:120]}


def add_filing_day(signals: list[dict], target: str, moves=None) -> list[dict]:
    """Each put carries `filing_day`: measured when its filing came in market hours (kept if an earlier run already
    measured it), else {market_hours: False}. Calls carry nothing (the tag is for puts only)."""
    moves = moves or FilingDayMoves()
    for s in signals:
        if s.get("side") != "PE" or (s.get("filing_day") or {}).get("D") is not None:
            continue
        if market_hours_filing(s.get("filed"), s.get("filed_time"), target):
            s["filing_day"] = moves.tag(s["symbol"], s["filed"], s["filed_time"])
        else:
            s["filing_day"] = {"market_hours": False, "tagged": False}
    return signals


# ---------------------------------------------------------------- the run
def chain_of(bhav: pd.DataFrame, sym: str, side: str) -> pd.DataFrame:
    b = bhav[(bhav["TckrSymb"] == sym) & (bhav["FinInstrmTp"] == "STO") & (bhav["OptnTp"] == side)].copy()
    b["XpryDt"] = b["XpryDt"].astype(str).str[:10]
    return b


def spot_of(bhav: pd.DataFrame, sym: str) -> float | None:
    u = bhav[(bhav["TckrSymb"] == sym) & (bhav["FinInstrmTp"] == "STO")]
    if "UndrlygPric" in u and (u["UndrlygPric"] > 0).any():
        return float(u.loc[u["UndrlygPric"] > 0, "UndrlygPric"].iloc[0])
    f = bhav[(bhav["TckrSymb"] == sym) & (bhav["FinInstrmTp"] == "STF")].sort_values("XpryDt")
    return float(f["ClsPric"].iloc[0]) if len(f) else None


def numbers(fin: dict, sym: str, filed: str, fetch: bool = True) -> dict:
    """The filing's quarter vs the one before and the year-ago one; fetches the stock's XBRL if the quarter is
    missing from data/financials.json (and stores it)."""
    from .financials import quarter_back
    from .peak_study import quarter_of, result_quality
    q = result_quality(fin, sym, filed)
    if q.get("net_profit") is not None or not fetch:
        return q
    from .events.http import FetchError
    from .financials import Fetcher
    qt = quarter_of(filed)
    try:
        rec = Fetcher().stock(sym, fin.get(sym), extra=(qt, quarter_back(qt, 1), quarter_back(qt, 4)))
    except FetchError as exc:
        log.warning("%s: results numbers unavailable (%s)", sym, exc)
        return q
    if rec:
        fin[sym] = rec
        fin["__changed__"] = True
    return result_quality(fin, sym, filed)


def run(now: datetime | None = None, state_path: Path = STATE_PATH, cache_dir: Path = ROOT / "data" / "cache",
        fetch: bool = True) -> dict:
    from server import sessions
    from .cm_fallback import IST
    from .events.store import Store
    from .financials import PATH as FIN_PATH, load as load_fin
    from .nse_fo import BhavcopyUnavailable, download_fo_bhavcopy
    from .universe import fetch_fo_lots

    now = now or datetime.now(IST)
    if fetch:
        refresh_holidays()
    target = target_session(now, sessions.is_session)
    cal = calendar(target, sessions.is_session)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    prior = dict(state)
    if state.get("session") and state["session"] != target.isoformat() and state.get("signals"):
        state["history"] = (state.get("history") or [])[-HISTORY_MAX:] + [
            {**s, "session": state["session"]} for s in state["signals"]]
    with Store() as st:
        results = [(e["symbol"], e["event_date"], e.get("event_time")) for e in st.all_of_type("results")
                   if e["event_date"] >= cal[0]]
        ban = {e["symbol"] for e in st.all_of_type("ban", since=target.isoformat())
               if e["event_date"] == target.isoformat() and e.get("subtype") == "in"}
    universe = set(fetch_fo_lots(cache_path=cache_dir / "fo_universe.txt"))
    bhav, last = None, None
    for d in reversed(cal[:-1]):                                      # the last session before the target
        try:
            bhav, last = download_fo_bhavcopy(date.fromisoformat(d), cache_dir), d
            break
        except (BhavcopyUnavailable, requests.RequestException, zipfile.BadZipFile, OSError, ValueError) as exc:
            log.info("%s: no F&O bhavcopy (%s)", d, exc)
    if bhav is not None:                                          # listing-day prices (S1 v12 below-Rs 2 rule)
        try:
            from .listing_prices import update as listing_update
            log.info("listing prices: %d contracts first traded on %s", listing_update(bhav, last), last)
        except Exception as exc:  # noqa: BLE001 - the signals must not depend on it
            log.warning("listing prices not updated: %s", exc)
    fin = load_fin()
    signals, skipped = [], []
    for sym, d, t in day0_signals(results, cal):
        base = {"symbol": sym, "filed": d, "filed_time": t}
        if sym not in universe:
            continue                                                  # not an F&O stock: not reported
        if bhav is None:
            skipped.append({**base, "reason": "no F&O bhavcopy for the last session"})
            continue
        q = numbers(fin, sym, d, fetch)
        side = classify(q)
        info = {**base, "quarter": q.get("quarter"), "np_yoy": num_or_none(q.get("net_profit_yoy")),
                "np_qoq": num_or_none(q.get("net_profit_qoq")), "rev_yoy": num_or_none(q.get("revenue_yoy")),
                "why": describe(q)}
        if q.get("net_profit") is None:
            skipped.append({**info, "reason": "net profit not in the filing's XBRL (yet)"})
            continue
        if side is None:
            skipped.append({**info, "reason": "numbers neither strong nor weak"})
            continue
        if sym in ban:
            skipped.append({**info, "side": side, "reason": "in the F&O ban on day 0"})
            continue
        ch = chain_of(bhav, sym, side)
        exp = choose_expiry(ch["XpryDt"], target, sessions.sessions_to_expiry) if len(ch) else None
        spot = spot_of(bhav, sym)
        if exp is None or not spot:
            skipped.append({**info, "side": side, "reason": "no option chain or expiry"})
            continue
        strikes = sorted(float(k) for k in ch.loc[ch["XpryDt"] == exp, "StrkPric"].unique())
        try:
            from .listing_prices import lookup as listing_lookup
            listing = listing_lookup(sym, side, exp)
        except Exception:  # noqa: BLE001
            listing = {}
        signals.append({**info, "side": side, "expiry": exp, "spot": round(spot, 2), "strikes": strikes,
                        "chain_from": last, "listing": listing})
    signals, skipped = keep_earlier(prior, target.isoformat(), signals, skipped)
    if prior.get("session") == target.isoformat():                # the morning run keeps the nightly measurement
        had = {s["symbol"]: s["filing_day"] for s in prior.get("signals") or [] if (s.get("filing_day") or {}).get("D") is not None}
        for s in signals:
            if s["symbol"] in had and (s.get("filing_day") or {}).get("D") is None:
                s["filing_day"] = had[s["symbol"]]
    if fin.pop("__changed__", False):
        FIN_PATH.write_text(json.dumps(fin, indent=0, sort_keys=True), encoding="utf-8")
    state.update({"rules": RULES_TEXT, "session": target.isoformat(), "made_at": now.isoformat(timespec="seconds"),
                  "signals": signals, "skipped": skipped,
                  "ban": sorted(ban)})                     # the session's F&O ban list: server/rules.py skips A / B in it
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=1), encoding="utf-8")
    log.info("fade signals for %s: %s; skipped %s", target, [(s["symbol"], s["side"]) for s in signals],
             [(s["symbol"], s["reason"]) for s in skipped])
    return state


def refresh_holidays(path: Path = ROOT / "data" / "nse_holidays.json") -> None:
    """NSE's F&O trading holidays -> data/nse_holidays.json (merged with the dates already there); kept as is when
    NSE does not answer. server/sessions.py reads the file, so the scanner and the live server share one calendar."""
    from .events.http import EventHttp, FetchError
    try:
        d = EventHttp().get_json("https://www.nseindia.com/api/holiday-master?type=trading",
                                 "https://www.nseindia.com/resources/exchange-communication-holidays")
        new = {datetime.strptime(x["tradingDate"], "%d-%b-%Y").date().isoformat() for x in (d or {}).get("FO") or []}
    except (FetchError, ValueError, KeyError, TypeError, AttributeError) as exc:
        log.warning("NSE holiday list unavailable (%s); keeping %s", exc, path.name)
        return
    if not new:
        return
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    days = sorted(set(old.get("holidays") or []) | new)
    if days != old.get("holidays"):
        path.write_text(json.dumps({"source": "https://www.nseindia.com/api/holiday-master?type=trading (FO)",
                                    "fetched": date.today().isoformat(), "holidays": days}, indent=1), encoding="utf-8")


def keep_earlier(prior: dict, target: str, signals: list[dict], skipped: list[dict]) -> tuple[list[dict], list[dict]]:
    """A rerun for the same session (the morning run) never drops a signal the earlier run made, unless it now finds
    the numbers neither strong nor weak; a stock it could not rebuild (NSE refused the bhavcopy, an empty event store)
    keeps the earlier signal."""
    if prior.get("session") != target:
        return signals, skipped
    have = {s["symbol"] for s in signals}
    judged = {s["symbol"] for s in skipped if s.get("reason") == "numbers neither strong nor weak"}
    kept = [{**s, "kept_from": prior.get("made_at")} for s in prior.get("signals") or []
            if s["symbol"] not in have and s["symbol"] not in judged]
    names = {s["symbol"] for s in kept}
    return signals + kept, [s for s in skipped if s["symbol"] not in names]


def patch_scan(scan_path: Path = ROOT / "data" / "scan.json", state_path: Path = STATE_PATH) -> bool:
    """The morning run: put the fresh signals into the committed scan (meta.fade) without rebuilding it."""
    if not (scan_path.exists() and state_path.exists()):
        return False
    scan = json.loads(scan_path.read_text(encoding="utf-8"))
    scan.setdefault("meta", {})["fade"] = json.loads(state_path.read_text(encoding="utf-8"))
    scan_path.write_text(json.dumps(scan, separators=(",", ":")), encoding="utf-8")
    return True


def fd2_pass(state_path: Path = STATE_PATH, moves=None) -> int:
    """The fd2 shadow tag on the signal file's puts (a separate step, run in its own venv with the Kotak SDK). Returns
    the number of puts measured; the file is rewritten only when something changed."""
    if not state_path.exists():
        return 0
    state = json.loads(state_path.read_text(encoding="utf-8"))
    before = json.dumps(state.get("signals"), sort_keys=True)
    add_filing_day(state.get("signals") or [], state.get("session") or "", moves)
    if json.dumps(state.get("signals"), sort_keys=True) != before:
        state_path.write_text(json.dumps(state, indent=1), encoding="utf-8")
    n = sum(1 for s in state.get("signals") or [] if (s.get("filing_day") or {}).get("market_hours"))
    log.info("fd2: %s", [(s["symbol"], s.get("filing_day")) for s in state.get("signals") or [] if s.get("side") == "PE"])
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 v10 results-day fade signals for the next session (paper only)")
    ap.add_argument("--patch-scan", action="store_true", help="also write them into data/scan.json (morning run)")
    ap.add_argument("--fd2", action="store_true", help="only add the fd2 shadow tag to the existing signal file")
    a = ap.parse_args()
    if a.fd2:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
        print(f"fd2: {fd2_pass()} market-hours puts")
        if a.patch_scan:
            print("scan patched" if patch_scan() else "no scan to patch")
        return
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    st = run()
    print(f"fade: {st['session']}: {len(st['signals'])} signals, {len(st['skipped'])} skipped")
    if a.patch_scan:
        print("scan patched" if patch_scan() else "no scan to patch")


if __name__ == "__main__":
    main()
