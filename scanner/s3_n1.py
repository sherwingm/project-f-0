"""S3 N1 (strategies/S3_N1_near_expiry_orb.md): NIFTY near-expiry opening-range breakout. On the weekly expiry day and
the session before it, the first 1-minute close outside the 09:15-09:29 range (09:30-13:00) buys a call (above) or a
put (below) 100 points out of the money in the nearest weekly, at the entry minute; 50 % stop; sold at 15:15. Research
only: nothing runs on the server, nothing is ordered. Strategy name in the code: `near_expiry`.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_n1            # forward (the verdict)
    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_n1 --history  # once, description only

Forward: the recorder's 1-second files (`<store>/nifty_1s`), bought at the ask, sold at the bid, charges from
server/charges.py; writes data/results/S3_N1_forward.md + _trades.csv. History: 2024-10-01 → 2026-10-28 option minutes,
minute closes + slippage (1 %: 2 strikes out); writes S3_N1_history.md + _trades.csv. Never pooled.
"""
from __future__ import annotations

import sys
from datetime import date

import numpy as np
import pandas as pd

from scanner.s3_b2 import signal
from scanner.s3_g1_forward import last_quote, load, minute_bars, sessions as recorded_sessions
from scanner.s3_p1 import t_stat
from scanner.s3_pods import RES
from server import charges
from server import sessions as S

PAGE = "strategies/S3_N1_near_expiry_orb.md"
STRATEGY = "near_expiry"
START = date(2026, 11, 6)
HIST = (date(2024, 10, 1), date(2026, 10, 28))
STOP, OUT, STEP, GATE_N, MAX_K, SLIP = 0.50, 2, 50, 30, 1, 0.01
EXIT = "15:15"


def strike_for(side: str, spot: float) -> float:
    atm = round(spot / STEP) * STEP
    return atm + OUT * STEP if side == "CE" else atm - OUT * STEP


def nearest_expiry(day: date, expiries) -> date | None:
    after = sorted(e for e in expiries if e >= day)
    return after[0] if after else None


def eligible(day: date, expiry: date | None) -> int | None:
    """Sessions left to `expiry` (0 = expiry day) when it is 0 or 1, else None (no trade that day)."""
    if expiry is None:
        return None
    k = S.sessions_to_expiry(day, expiry)
    return k if k <= MAX_K else None


def _result(base: dict, paid: float, sold: float, lot: int, opt: str, why: str, t_out, max_up) -> dict:
    ch = charges.leg(opt, "BUY", lot, paid)["total"] + charges.leg(opt, "SELL", lot, sold)["total"]
    gross = (sold - paid) * lot
    return {**base, "skip": "", "exit_at": t_out.strftime("%H:%M:%S"), "reason": why, "paid": round(paid, 2),
            "sold": round(sold, 2), "qty": lot, "gross_rs": round(gross, 2), "fees_rs": round(ch, 2),
            "net_rs": round(gross - ch, 2), "net_pct": round((gross - ch) / (paid * lot) * 100, 2),
            "net_pct_2x": round((gross - 2 * ch) / (paid * lot) * 100, 2), "max_up_held_pct": max_up}


# ---------------------------------------------------------------- forward (1-second recorder files)
def book(day: date, d1: pd.DataFrame, lot: int = 65, expiries=None) -> dict | None:
    """One session's trade, a row with `skip`, or None (not an eligible day, or no breakout)."""
    opts = d1[d1["kind"].isin(["CE", "PE"])]
    exps = [date.fromisoformat(e) for e in opts["expiry"].dropna().unique()] if expiries is None else expiries
    ex = nearest_expiry(day, exps)
    k = eligible(day, ex)
    if k is None:
        return None
    bars = minute_bars(d1)
    sg = signal(bars, 15, None)
    if sg is None:
        return None
    side, ent = sg[0], sg[1] + pd.Timedelta(minutes=1)
    base = {"day": day, "strategy": STRATEGY, "sessions_left": k, "side": side, "signal": sg[1].strftime("%H:%M"),
            "entry": ent.strftime("%H:%M"), "expiry": ex.isoformat()}
    spot = bars.loc[bars["timestamp"] == sg[1], "close"]
    kk = strike_for(side, float(spot.iloc[0]))
    base.update({"strike": kk, "spot": float(spot.iloc[0])})
    q = opts[(opts["kind"] == side) & (opts["expiry"] == ex.isoformat()) & (opts["strike"] == kk)].sort_values("timestamp")
    paid, t_paid = last_quote(q, ent, "a")
    if paid is None:
        return {**base, "skip": f"no ask for {kk:.0f} {side} in the entry minute"}
    out_min = pd.Timestamp(f"{day} {EXIT}", tz=t_paid.tz)
    path = q[(q["timestamp"] > t_paid) & (q["timestamp"] < out_min + pd.Timedelta(seconds=60))]
    hit = path[path["bl"].notna() & (path["bl"] <= paid * (1 - STOP))]
    if len(hit):
        sold, t_out, why = float(hit["bl"].iloc[0]), hit["timestamp"].iloc[0], "stop"
    else:
        sold, t_out = last_quote(q, out_min, "bc")
        why = EXIT
        if sold is None:
            if out_min > q["timestamp"].max() if len(q) else True:
                return {**base, "skip": "session not complete in the file", "pending": True}
            return {**base, "skip": f"no bid for {kk:.0f} {side} at {EXIT}"}
    held = path[path["timestamp"] <= t_out]
    mu = round((held["bc"].max() / paid - 1) * 100, 1) if held["bc"].notna().any() else np.nan
    return _result(base, paid, sold, lot, side, why, t_out, mu)


def collect_forward() -> pd.DataFrame:
    rows = []
    for day in recorded_sessions():
        if day >= START:
            r = book(day, load(day))
            if r is not None:
                rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- history (1-minute options, description only)
def book_history(day: date, spot: pd.DataFrame, chain: pd.DataFrame, expiry: date, k: int, lot: int) -> dict | None:
    sg = signal(spot, 15, None)
    if sg is None:
        return None
    side, ent = sg[0], sg[1] + pd.Timedelta(minutes=1)
    s0 = float(spot.loc[spot["timestamp"] == sg[1], "close"].iloc[0])
    kk = strike_for(side, s0)
    base = {"day": day, "strategy": STRATEGY, "sessions_left": k, "side": side, "signal": sg[1].strftime("%H:%M"),
            "entry": ent.strftime("%H:%M"), "expiry": expiry.isoformat(), "strike": kk, "spot": s0}
    c = chain[(chain["strike"] == kk) & (chain["option_type"] == side)].sort_values("timestamp")
    e = c[(c["timestamp"] <= ent) & (c["timestamp"] > ent - pd.Timedelta(minutes=3))]
    if e.empty:
        return {**base, "skip": f"no trade in {kk:.0f} {side} within 3 minutes of entry"}
    paid = float(e["close"].iloc[-1]) * (1 + SLIP)
    out = pd.Timestamp(f"{day} {EXIT}", tz=c["timestamp"].dt.tz) if len(c) else pd.Timestamp(f"{day} {EXIT}")
    path = c[(c["timestamp"] > ent) & (c["timestamp"] <= out)]
    lvl = paid * (1 - STOP)
    hit = path[path["low"] <= lvl]
    if len(hit):
        h = hit.iloc[0]
        sold, t_out, why = min(float(h["open"]), lvl) * (1 - SLIP), h["timestamp"], "stop"
    else:
        x = c[(c["timestamp"] <= out) & (c["timestamp"] > out - pd.Timedelta(minutes=30))]
        if x.empty:
            return {**base, "skip": f"no trade in {kk:.0f} {side} in the 30 minutes to {EXIT}"}
        sold, t_out, why = float(x["close"].iloc[-1]) * (1 - SLIP), out, EXIT
    held = path[path["timestamp"] <= t_out]
    mu = round((held["high"].max() / paid - 1) * 100, 1) if len(held) else np.nan
    return _result(base, paid, sold, lot, side, why, t_out, mu)


def collect_history() -> pd.DataFrame:
    from index_data import load as L
    exps = [e for e in L.expiries("NIFTY") if HIST[0] <= e <= HIST[1]]
    rows = []
    for ex in exps:
        for d in L.trade_days("NIFTY", ex):
            k = eligible(d, ex) if HIST[0] <= d <= ex else None
            if k is None or nearest_expiry(d, exps) != ex:
                continue
            spot = L.spot_1m(d, d)
            ch = L.options_day("NIFTY", ex, d)
            if spot.empty or ch.empty:
                continue
            r = book_history(d, spot.reset_index(drop=True), ch, ex, k, L.lot_on(d, "NIFTY", ex))
            if r is not None:
                rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- report
def gate(t: pd.DataFrame) -> list[tuple[str, bool]]:
    t = t.head(GATE_N)
    month = t.groupby(pd.to_datetime(t["day"]).dt.to_period("M"))["net_rs"].sum().mean()
    return [(f"{GATE_N} trades", len(t) >= GATE_N), ("mean > 0", t["net_pct"].mean() > 0),
            ("mean > 0 at 2x charges", t["net_pct_2x"].mean() > 0), ("t ≥ 2", t_stat(t["net_pct"]) >= 2),
            ("both halves positive", t["net_pct"].iloc[:15].mean() > 0 and t["net_pct"].iloc[15:].mean() > 0),
            ("worst trade smaller than the average month", -t["net_rs"].min() < month)]


def summary(ok: pd.DataFrame) -> list[str]:
    if ok.empty:
        return ["- No trades booked."]
    x = ok["net_pct"]
    out = [f"- {len(ok)} trades. Mean {x.mean():+.1f} % of the premium (median {x.median():+.1f} %, t {t_stat(x):.2f}), "
           f"won {(x > 0).mean() * 100:.0f} %, total ₹{ok['net_rs'].sum():,.0f}; at 2× charges {ok['net_pct_2x'].mean():+.1f} %; "
           f"worst ₹{ok['net_rs'].min():,.0f}; stopped {(ok['reason'] == 'stop').mean() * 100:.0f} %",
           f"- Max up while held: mean {ok['max_up_held_pct'].mean():+.0f} %, median {ok['max_up_held_pct'].median():+.0f} %, "
           f"≥ +100 % on {(ok['max_up_held_pct'] >= 100).sum()} ({(ok['max_up_held_pct'] >= 100).mean() * 100:.0f} %)", "",
           "| Group | Trades | Mean | Median | t | Won | Total ₹ |", "|---|---|---|---|---|---|---|"]
    groups = [("Calls", ok["side"] == "CE"), ("Puts", ok["side"] == "PE"), ("Expiry day", ok["sessions_left"] == 0),
              ("Day before", ok["sessions_left"] == 1)]
    if "day" in ok and len(ok) > 1:
        mid = sorted(ok["day"])[len(ok) // 2]
        groups += [("First half", ok["day"] < mid), ("Second half", ok["day"] >= mid)]
    for n, m in groups:
        g = ok[m]["net_pct"]
        if len(g):
            out.append(f"| {n} | {len(g)} | {g.mean():+.1f} % | {g.median():+.1f} % | {t_stat(g):.2f} | "
                       f"{(g > 0).mean() * 100:.0f} % | {ok[m]['net_rs'].sum():,.0f} |")
    return out


def report(df: pd.DataFrame, history: bool) -> list[str]:
    ok = df[df["skip"].fillna("") == ""] if len(df) else df
    if history:
        head = [f"# S3 N1 history · {HIST[0]} → {HIST[1]} (description only, in-sample, not the verdict)", "",
                f"Pre-registered: `{PAGE}`. Minute closes + {SLIP * 100:.0f} % slippage a fill, charges from "
                f"`server/charges.py`, the lot of the day. Shown beside the forward result, never pooled with it."]
    else:
        head = [f"# S3 N1 forward · near-expiry ORB, sold {EXIT} · from {START}", "",
                f"Pre-registered: `{PAGE}`. Bought at the real ask, sold at the real bid (1-second recorder), "
                f"charges from `server/charges.py`. Verdict at the {GATE_N}th trade."]
    out = head + ["", f"Skipped days: {int((df['skip'].fillna('') != '').sum()) if len(df) else 0}", ""] + summary(ok)
    if not history:
        if len(ok) >= GATE_N:
            ch = gate(ok)
            out += ["", f"Verdict: **{'PASS' if all(c for _, c in ch) else 'FAIL'}**", ""] + \
                   [f"- {'✔' if c else '✘'} {n}" for n, c in ch]
        else:
            out += ["", f"Verdict: not yet ({len(ok)} of {GATE_N} trades)."]
    return out


def main():
    history = "--history" in sys.argv
    df = collect_history() if history else collect_forward()
    name = "S3_N1_history" if history else "S3_N1_forward"
    df.to_csv(RES / f"{name}_trades.csv", index=False)
    lines = report(df, history)
    (RES / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
