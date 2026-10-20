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
RULES_TEXT = ("S1 v11 results-day fade, paper only: on the first full session after a results filing, strong numbers "
              "(net profit YoY > +10 %, QoQ > 0, revenue YoY > 0) -> buy a put; weak numbers (net profit YoY < -10 %, "
              "QoQ < 0) -> buy a call. 1 lot at the live ask, Rs 600-8,000, walking away from the money from the "
              "strike nearest the live price, any time 09:15-15:20. Sold at the best bid once it is at or below "
              "0.80 x entry from 09:16 (-20 % stop), else at 15:20 the same day.")


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
        signals.append({**info, "side": side, "expiry": exp, "spot": round(spot, 2), "strikes": strikes,
                        "chain_from": last})
    signals, skipped = keep_earlier(prior, target.isoformat(), signals, skipped)
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


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 v10 results-day fade signals for the next session (paper only)")
    ap.add_argument("--patch-scan", action="store_true", help="also write them into data/scan.json (morning run)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    st = run()
    print(f"fade: {st['session']}: {len(st['signals'])} signals, {len(st['skipped'])} skipped")
    if a.patch_scan:
        print("scan patched" if patch_scan() else "no scan to patch")


if __name__ == "__main__":
    main()
