"""S1 forward paper test: the S1 v7 rules without near-expiry trades, run on new sessions only, one session at a
time, from NSE's end-of-day files. Paper only; nothing is ordered.

    python -m scanner.forward_s1            # process every session since the last one in the state file

Rules (strategies/S1_v7_results_beat_near_expiry.md, variant `old_expiry`): a results beat (day-0 return >= 2 %
above the leave-one-out sector, raw move < 10 %) is bought next session as one call lot: the current monthly expiry
if >= 10 sessions remain after day 0, else the next monthly; walking up from the at-the-money strike to the first
call with >= 50 contracts that day and one lot at Rs 600-8,000 (fill = the day's VWAP + 1 tick). Exits on each close
from the entry day: 50 % stop, 5 sessions without a new closing high, T-1. Arm A takes every beat, arm B only beats
in a strong sector. One position per stock and arm, 10-session cooldown.

Each session, in order: fill yesterday's signals, mark open trades (and keep following closed ones until their T-1
day, for the after-exit peak and dip), then record the session's new signals as "buy next session".
State: data/forward/s1_forward.json (committed by the nightly Action).
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from . import backtest_s1_v4 as v4
from . import backtest_s1_v6 as v6
from . import backtest_s1_v7 as v7
from .backtest_cheap_options import sessions_to
from .backtest_s1_v2 import Inputs, Market, day0_index
from .build import ROOT
from .option_engine import TICK
from .trade_sheet import span

log = logging.getLogger("forward_s1")

STATE_PATH = ROOT / "data" / "forward" / "s1_forward.json"
FIRST_SESSION = "2026-10-13"                      # signals from this session's results; entries from the next one
RULE = v7.Variant("old_expiry", near_expiry=False)
CONTRACTS, BAND = v7.NORMAL_CONTRACTS, v7.NORMAL_BAND
LOOKBACK_DAYS = 150                               # calendar days of closes loaded (>= 64 sessions for arm B)
RULES_TEXT = ("S1 v7 rules without near-expiry trades: results beat (day-0 move >= 2 % above its sector, < 10 % raw) "
              "-> next session buy 1 call lot, current monthly expiry if >= 10 sessions remain else next monthly, "
              "first strike from at-the-money upward with >= 50 contracts and Rs 600-8,000 a lot, at the day's "
              "average price + 1 tick. Exit at the close: 50 % stop, 5 sessions without a new closing high, or T-1. "
              "Failed the 2021-24 backtest gate (DECISIONS.md); paper only.")


# ---------------------------------------------------------------- state
def empty_state() -> dict:
    return {"rules": RULES_TEXT, "first_session": FIRST_SESSION, "last_session": None, "sessions": [],
            "arms": {a: {"pending": [], "open": [], "closed": [], "refused": []} for a in v4.ARMS}}


def load_state(path: Path = STATE_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else empty_state()


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    for arm in state["arms"].values():
        for t in arm["open"] + arm["closed"]:
            t["stats"] = stats(t)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=1), encoding="utf-8")


def stats(t: dict) -> dict:
    """Max peak (upside only) and max dip (downside only) of the closing premium while held and after the exit,
    % of the entry price, with dates; the last close and its P&L % for an open trade."""
    path = [(d, c) for d, c in t.get("path", []) if c is not None]
    end = t.get("exit_date") or "9999-12-31"
    held, after = span([p for p in path if p[0] <= end], t["entry_price"]), \
        span([p for p in path if p[0] > end], t["entry_price"])
    out = {f"h_{k}": v for k, v in held.items() if k != "high"}
    out.update({f"a_{k}": v for k, v in after.items() if k != "high"})
    out["above_exit"] = None if after["high"] is None or t.get("exit_price") is None else after["high"] > t["exit_price"]
    if path:
        out["last_date"], out["last_close"] = path[-1]
        out["mark_pct"] = round((path[-1][1] / t["entry_price"] - 1) * 100, 2)
    return out


# ---------------------------------------------------------------- one session (pure given its data)
def fill_pending(arm: dict, session: str, prices: pd.DataFrame | None, ban: set[str], category) -> list[dict]:
    """Yesterday's signals -> open trades (or refusals with the reason), at this session's VWAP."""
    opened = []
    for p in arm["pending"]:
        why = None
        if p["symbol"] in ban:
            why = "in the F&O ban on the entry day"
        elif prices is None:
            why = "no option prices for the entry day"
        else:
            w = v6.walk_strike(p["strikes"], p["spot"], v6.day1_quotes(prices, p["symbol"], p["expiry"]), CONTRACTS,
                               band=BAND)
            if isinstance(w, str):
                why = {"walk_below_band": "cheapest liquid lot below Rs 600",
                       "walk_no_liquid_strike_in_band": "no strike with >= 50 contracts and a lot in Rs 600-8,000",
                       "lottery_refused": "premium below Rs 2", "no_strike_or_expiry": "no strike"}.get(w, w)
            else:
                q, px, src, walked = w
                t = {k: p[k] for k in ("arm", "symbol", "sector", "signal_date", "beat", "move", "expiry", "spot")}
                t.update({"id": f"{p['arm']}:{p['symbol']}:{session}", "entry_date": session, "strike": q.strike,
                          "strikes_walked": walked, "lot": q.lot, "contracts_day1": q.contracts,
                          "entry_price": px, "entry_source": src, "cost": round(px * q.lot, 2),
                          "category": category(p["symbol"], session)[0], "best": px, "stall": 0,
                          "fut0": None, "stock0": None, "path": [], "exit_date": None, "exit_reason": None,
                          "exit_price": None, "net": None, "net_pct": None, "excluded": "", "tracking": True})
                opened.append(t)
        if why:
            arm["refused"].append({**{k: p[k] for k in ("arm", "symbol", "signal_date", "beat", "move")},
                                   "entry_date": session, "reason": why})
    arm["pending"] = []
    arm["open"].extend(opened)
    return opened


def mark(arm: dict, session: str, day: dict, stock_close, cal_dates: list[date]) -> list[dict]:
    """Each open trade's close this session through the exit rules; closed trades keep collecting closes until
    their T-1 day. `day` is v4.Days.bhav's dict; `stock_close(symbol)` the stock's close this session."""
    closed_now = []
    for t in list(arm["open"]):
        c = day["calls"].get((t["symbol"], t["expiry"], float(t["strike"])))
        if c is None:
            t.update(excluded="contract_changed", exit_date=session, tracking=False)
            arm["open"].remove(t)
            arm["closed"].append(t)
            continue
        f, px = day["futs"].get((t["symbol"], t["expiry"])), stock_close(t["symbol"])
        if t["fut0"] is None:
            t["fut0"], t["stock0"] = f, px
        elif f and t["fut0"] and t["stock0"] and px and not math.isnan(px) and \
                abs((f / t["fut0"]) / (px / t["stock0"]) - 1) > v4.CA_TOLERANCE:
            t.update(excluded="price_adjusted", exit_date=session, tracking=False)
            arm["open"].remove(t)
            arm["closed"].append(t)
            continue
        t["path"].append([session, c])
        left = sessions_to(cal_dates, date.fromisoformat(session), date.fromisoformat(t["expiry"]))
        t["best"], t["stall"], reason = v7.exit_step(c, t["entry_price"], t["best"], t["stall"], left, RULE.stop)
        if reason:
            exit_px = max(0.0, round(c - TICK, 2))
            slip = v4.SLIPPAGE.get(t["category"], v4.SLIPPAGE["unknown"])
            charges, slippage, net = v4.net_of(t["entry_price"], exit_px, t["lot"], slip)
            t.update(exit_date=session, exit_reason=reason, exit_price=exit_px, charges=charges, slippage=slippage,
                     net=net, net_pct=round(net / t["cost"] * 100, 2), tracking=left > v7.T_MINUS)
            arm["open"].remove(t)
            arm["closed"].append(t)
            closed_now.append(t)
    for t in arm["closed"]:                              # after the exit: follow the premium until T-1
        if not t.get("tracking") or t["exit_date"] >= session:
            continue
        c = day["calls"].get((t["symbol"], t["expiry"], float(t["strike"])))
        left = sessions_to(cal_dates, date.fromisoformat(session), date.fromisoformat(t["expiry"]))
        if c is not None:
            t["path"].append([session, c])
        if c is None or left <= v7.T_MINUS:
            t["tracking"] = False
    return closed_now


def open_pick(p: dict, prices: pd.DataFrame | None) -> dict:
    """The strike for the next open's entry: the rules' walk on day 0's prices."""
    if prices is None:
        return {"open_strike": None, "open_reason": "no option prices for the results day"}
    w = v6.walk_strike(p["strikes"], p["spot"], v6.day1_quotes(prices, p["symbol"], p["expiry"]), CONTRACTS, band=BAND)
    if isinstance(w, str):
        return {"open_strike": None, "open_reason": {"walk_below_band": "cheapest liquid lot below Rs 600",
                                                     "walk_no_liquid_strike_in_band": "no strike with >= 50 contracts "
                                                     "and a lot in Rs 600-8,000 on the results day",
                                                     "lottery_refused": "premium below Rs 2"}.get(w, w)}
    q, px, _src, _walked = w
    return {"open_strike": q.strike, "open_lot": q.lot, "open_ref": px}


def blocked(state_arm: dict, symbol: str, i0: int, pos: dict[str, int]) -> bool:
    """One position per stock and arm, and v4's 10-session cooldown after an exit."""
    if any(x["symbol"] == symbol for x in state_arm["pending"] + state_arm["open"]):
        return True
    return any(x["symbol"] == symbol and x.get("exit_date") in pos and i0 <= pos[x["exit_date"]] + v4.COOLDOWN
               for x in state_arm["closed"])


def new_signals(state: dict, session: str, m: Market, results: list, day: dict, funnel: Counter,
                prices: pd.DataFrame | None = None) -> list[dict]:
    """Results beats with day 0 = this session -> pending ("buy next session") in each arm that takes them. With
    the session's option prices, the strike the live paper account buys at the next open is picked here too
    (server/rules.py): the same walk on day 0's volume and average price."""
    i = m.pos[session]
    universe = {session: set(day["chain"])}
    sigs = v4.signals(m, results, universe, session, 10 ** 9, funnel)
    added = []
    for s in sigs:
        if s.i0 != i:
            continue
        chain = day["chain"].get(s.symbol)
        spot = day["spot"].get(s.symbol)
        ch = v7.choose_expiry(chain["XpryDt"], m.cal_dates, m.cal_dates[i], near_ok=False) \
            if chain is not None else None
        for arm in v4.ARMS:
            if arm == "B" and not v4.strong_sector(s.state):
                continue
            st = state["arms"][arm]
            base = {"arm": arm, "symbol": s.symbol, "sector": m.sector_of.get(s.symbol, ""), "signal_date": session,
                    "beat": round(s.ar0, 2), "move": round(s.raw, 2)}
            if blocked(st, s.symbol, i, m.pos):
                st["refused"].append({**base, "entry_date": None, "reason": "already holding / 10-session cooldown"})
                continue
            if ch is None or not spot:
                st["refused"].append({**base, "entry_date": None, "reason": "no option chain or expiry"})
                continue
            exp = ch[0]
            p = {**base, "expiry": exp, "spot": float(spot),
                 "strikes": sorted(float(k) for k in chain.loc[chain["XpryDt"] == exp, "StrkPric"].unique())}
            p.update(open_pick(p, prices))
            st["pending"].append(p)
            added.append(p)
    return added


def step(state: dict, session: str, m: Market, day: dict, prices: pd.DataFrame | None, results: list,
         ban: set[str], category) -> dict:
    """One session: fill, mark, new signals. Returns a log line."""
    stock_close = lambda s: float(m.close[s][m.pos[session]]) if s in m.close else math.nan   # noqa: E731
    line = {"session": session}
    for arm_name, arm in state["arms"].items():
        opened = fill_pending(arm, session, prices, ban, category)
        closed = mark(arm, session, day, stock_close, m.cal_dates)
        line[arm_name] = {"filled": [t["symbol"] for t in opened], "exited": [t["symbol"] for t in closed]}
    funnel = Counter()
    added = new_signals(state, session, m, results, day, funnel, prices)
    for arm_name in state["arms"]:
        line[arm_name]["signals"] = [p["symbol"] for p in added if p["arm"] == arm_name]
    state["sessions"].append(line)
    state["last_session"] = session
    return line


# ---------------------------------------------------------------- data for the nightly run
def market(symbols: set[str], eod2_dir: Path, cache_dir: Path, today: date) -> Market:
    """Closes of `symbols` and their sectors' members plus NIFTY 500, eod2 + NSE's cash-market file for the days
    eod2 lacks, on the NIFTY 500 calendar."""
    from .cm_fallback import fill, fill_index
    from .equity import load_symbol
    from .sectors import BENCHMARK, index_closes, load_map

    sector_of = load_map()
    sectors = {sector_of[s] for s in symbols if s in sector_of}
    need = set(symbols) | {s for s, k in sector_of.items() if k in sectors}
    since = pd.Timestamp(today - timedelta(days=LOOKBACK_DAYS * 3))
    frames = {}
    for s in sorted(need):
        try:
            f = load_symbol(s, eod2_dir)
            frames[s] = f[f.index >= since]
        except Exception as exc:  # noqa: BLE001 - not every stock has eod2 history
            log.info("%s: no eod2 (%s)", s, exc)
    days = fill(frames, cache_dir, today)
    bench = index_closes(BENCHMARK, eod2_dir)
    bench = fill_index(bench[bench.index >= since], days, name=BENCHMARK)
    cal = [d.strftime("%Y-%m-%d") for d in bench.index]
    return Market(Inputs(cal=cal, bhav=lambda d: None, opens=lambda d: None,
                         stock={s: f["Close"] for s, f in frames.items()}, sector_of=sector_of, bench=bench))


def run(today: date | None = None, state_path: Path = STATE_PATH, eod2_dir: Path = ROOT / "data" / "eod2",
        cache_dir: Path = ROOT / "data" / "cache") -> dict:
    from . import amfi
    from .events.store import Store
    from .nse_fo import BhavcopyUnavailable, download_fo_bhavcopy, download_fo_prices

    from .cm_fallback import IST

    today = today or datetime.now(IST).date()
    state = load_state(state_path)
    start = date.fromisoformat(state["last_session"]) + timedelta(days=1) if state["last_session"] \
        else date.fromisoformat(state["first_session"])
    todo = []
    d = start
    while d <= today:
        if d.weekday() < 5:
            try:
                download_fo_bhavcopy(d, cache_dir)
                todo.append(d.isoformat())
            except BhavcopyUnavailable as exc:
                log.info("%s: no F&O bhavcopy (%s)", d, exc)
        d += timedelta(days=1)
    if not todo:
        log.info("no new session since %s", state["last_session"])
        save_state(state, state_path)
        return state
    with Store() as st:
        results = [(e["symbol"], e["event_date"], e.get("event_time")) for e in st.all_of_type("results")]
        ban: dict[str, set[str]] = {}
        for e in st.all_of_type("ban"):
            if e.get("subtype") == "in":
                ban.setdefault(e["event_date"], set()).add(e["symbol"])
    held = {t["symbol"] for a in state["arms"].values() for t in a["open"] + a["closed"] + a["pending"]}
    lo = (date.fromisoformat(todo[0]) - timedelta(days=7)).isoformat()
    candidates = {s for s, d0, _ in results if d0 >= lo}
    m = market(candidates | held, eod2_dir, cache_dir, today)
    cats = amfi.load()
    days = v4.Days(cache_dir, prices=None)
    for session in todo:
        if session not in m.pos:
            log.warning("%s: no closes for the session yet (cash-market or index file missing); stopping", session)
            break
        try:
            prices = download_fo_prices(date.fromisoformat(session), cache_dir)
        except BhavcopyUnavailable as exc:
            log.warning("%s: option prices unavailable (%s)", session, exc)
            prices = None
        line = step(state, session, m, days.bhav(session), prices, results, ban.get(session, set()), cats.category_on)
        log.info("%s: %s", session, json.dumps({k: v for k, v in line.items() if k != "session"}))
    save_state(state, state_path)
    return state


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 forward paper test (night list + night fill)")
    ap.add_argument("--today", type=date.fromisoformat)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    st = run(a.today)
    for arm, x in st["arms"].items():
        print(f"arm {arm}: pending {len(x['pending'])}, open {len(x['open'])}, closed {len(x['closed'])}, "
              f"refused {len(x['refused'])}")


if __name__ == "__main__":
    main()
