"""S3 G1 forward test (strategies/S3_G1_put_overnight.md): NIFTY downside opening-range breakout, ATM put bought at
the ask, 50 % stop on the bid, held overnight and sold at the bid of the next session's 09:16. Research only: reads the
1-second files `index_data.pull_1s` copies from the live recorder; nothing runs on the server, nothing is ordered.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_g1_forward

Re-books every session from START each run (idempotent) and writes data/results/S3_G1_forward.md + _trades.csv.
"""
from __future__ import annotations

import math
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

from index_data.common import STORE
from scanner.s3_b2 import signal
from scanner.s3_p1 import t_stat
from scanner.s3_pods import RES
from server import charges

PAGE = "strategies/S3_G1_put_overnight.md"
START = date(2026, 11, 5)
STOP, LOT, STEP, GATE_N, QUOTE_AGE = 0.50, 65, 50, 30, 60
GAP_MAX, WIDTH_SKIP, VIX_MAX = 0.3, (0.5, 0.8), 17.0      # G1-F skips (page: "Second track")
FOLDER = STORE / "nifty_1s"


def sessions() -> list[date]:
    return sorted(date.fromisoformat(p.stem) for p in FOLDER.glob("*.parquet"))


def load(day: date) -> pd.DataFrame:
    return pd.read_parquet(FOLDER / f"{day}.parquet")


def minute_bars(day_1s: pd.DataFrame, symbol: str = "NIFTY 50") -> pd.DataFrame:
    """1-minute OHLC of a symbol's 1-second last prices, stamped with the minute's start (as the history's bars)."""
    s = day_1s[day_1s["symbol"] == symbol].sort_values("timestamp")
    g = s.groupby(s["timestamp"].dt.floor("min"))
    out = pd.DataFrame({"open": g["o"].first(), "high": g["h"].max(), "low": g["l"].min(), "close": g["c"].last()})
    return out.reset_index().rename(columns={"index": "timestamp"})


def quotes(day_1s: pd.DataFrame, expiry: str, strike: float, opt: str = "PE") -> pd.DataFrame:
    q = day_1s[(day_1s["kind"] == opt) & (day_1s["expiry"] == expiry) & (day_1s["strike"] == strike)]
    return q.sort_values("timestamp")[["timestamp", "bc", "bl", "a"]].reset_index(drop=True)


def last_quote(q: pd.DataFrame, minute: pd.Timestamp, col: str):
    """The column's last valid value inside the minute [minute, minute + 60 s), at most QUOTE_AGE s before its end."""
    end = minute + pd.Timedelta(seconds=60)
    w = q[(q["timestamp"] < end) & q[col].notna() & (q[col] > 0)]
    if w.empty or (end - w["timestamp"].iloc[-1]).total_seconds() > QUOTE_AGE:
        return None, None
    return float(w[col].iloc[-1]), w["timestamp"].iloc[-1]


def g1f_skip(d1: pd.DataFrame, bars: pd.DataFrame, sig_min: pd.Timestamp, prev_close: float | None) -> tuple[str, dict]:
    """("" or the reasons G1-F skips the day, the three filter values), all known at the signal minute."""
    t = bars["timestamp"].dt.time
    rng = bars[(t >= pd.Timestamp("09:15").time()) & (t < pd.Timestamp("09:30").time())]
    hi, lo = float(rng["high"].max()), float(rng["low"].min())
    width = (hi - lo) / lo * 100
    gap = (float(bars["open"].iloc[0]) / prev_close - 1) * 100 if prev_close else None
    vx = d1[(d1["symbol"] == "INDIA VIX") & (d1["timestamp"] < sig_min + pd.Timedelta(seconds=60))]["c"].dropna()
    vix = float(vx.iloc[-1]) if len(vx) else None
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
    return "; ".join(why), {"day1_gap_pct": gap, "or_width_pct": round(width, 3), "vix_signal": vix}


def book(day: date, d1: pd.DataFrame, nxt: date | None, d2: pd.DataFrame | None, prev_close: float | None = None) -> dict:
    """One session's trade, a row with `skip`, or None (no downside first breakout). `g1f_skip` says whether the
    G1-F track also takes it ("" = it does)."""
    bars = minute_bars(d1)
    sg = signal(bars, 15, None)
    if sg is None or sg[0] != "PE":
        return None
    ent = sg[1] + pd.Timedelta(minutes=1)
    fs, fv = g1f_skip(d1, bars, sg[1], prev_close)
    base = {"day": day, "signal": sg[1].strftime("%H:%M"), "entry": ent.strftime("%H:%M"), "g1f_skip": fs, **fv}
    spot = bars.loc[bars["timestamp"] == ent, "close"]
    if spot.empty:
        return {**base, "skip": "no NIFTY bar at entry"}
    k = round(float(spot.iloc[0]) / STEP) * STEP
    exps = sorted(e for e in d1.loc[d1["kind"] == "PE", "expiry"].dropna().unique() if date.fromisoformat(e) > day)
    if not exps:
        return {**base, "skip": "no expiry after the day recorded"}
    ex = exps[0]
    base.update({"expiry": ex, "strike": k, "spot": float(spot.iloc[0])})
    q1 = quotes(d1, ex, k)
    paid, t_paid = last_quote(q1, ent, "a")
    if paid is None:
        return {**base, "skip": f"no ask for {k:.0f} PE in the entry minute"}
    if nxt is None or d2 is None:
        return {**base, "skip": "waiting for the next session's file", "pending": True}
    q2 = quotes(d2, ex, k)
    out_min = pd.Timestamp(f"{nxt} 09:16", tz=t_paid.tz)
    path = pd.concat([q1[q1["timestamp"] > t_paid], q2[q2["timestamp"] < out_min + pd.Timedelta(seconds=60)]])
    hit = path[path["bl"].notna() & (path["bl"] <= paid * (1 - STOP))]
    if len(hit):
        sold, t_out, why = float(hit["bl"].iloc[0]), hit["timestamp"].iloc[0], "stop"
    else:
        sold, t_out = last_quote(q2, out_min, "bc")
        why = "next open"
        if sold is None:
            return {**base, "skip": f"no bid for {k:.0f} PE at {nxt} 09:16"}
    held = path[path["timestamp"] <= t_out]
    whole = pd.concat([q1[q1["timestamp"] > t_paid], q2])
    ch = charges.leg("PE", "BUY", LOT, paid)["total"] + charges.leg("PE", "SELL", LOT, sold)["total"]
    gross = (sold - paid) * LOT
    gap = None
    b2 = minute_bars(d2)
    if len(b2) and len(bars):
        gap = (float(b2["open"].iloc[0]) / float(bars["close"].iloc[-1]) - 1) * 100
    return {**base, "skip": "", "exit_day": t_out.date(), "exit_at": t_out.strftime("%H:%M:%S"), "reason": why, "paid": paid,
            "sold": sold, "qty": LOT, "gross_rs": round(gross, 2), "fees_rs": round(ch, 2),
            "net_rs": round(gross - ch, 2), "net_pct": round((gross - ch) / (paid * LOT) * 100, 2),
            "net_pct_2x": round((gross - 2 * ch) / (paid * LOT) * 100, 2),
            "max_up_held_pct": round((held["bc"].max() / paid - 1) * 100, 1) if held["bc"].notna().any() else np.nan,
            "max_up_to_1529_pct": round((whole["bc"].max() / paid - 1) * 100, 1) if whole["bc"].notna().any() else np.nan,
            "gap_pct": round(gap, 3) if gap is not None else None}


def collect() -> pd.DataFrame:
    ses = sessions()
    rows = []
    for i, day in enumerate(ses):
        if day < START:
            continue
        nxt = ses[i + 1] if i + 1 < len(ses) else None
        prev = ses[i - 1] if i else None
        pc = None
        if prev is not None:
            n50 = load(prev)
            n50 = n50[n50["symbol"] == "NIFTY 50"].sort_values("timestamp")["c"].dropna()
            pc = float(n50.iloc[-1]) if len(n50) else None
        r = book(day, load(day), nxt, load(nxt) if nxt else None, pc)
        if r is not None:
            rows.append(r)
    return pd.DataFrame(rows)


def gate(t: pd.DataFrame) -> list[tuple[str, bool]]:
    t = t.head(GATE_N)
    month = t.groupby(pd.to_datetime(t["day"]).dt.to_period("M"))["net_rs"].sum().mean()
    return [(f"{GATE_N} trades", len(t) >= GATE_N), ("mean > 0", t["net_pct"].mean() > 0),
            ("mean > 0 at 2x charges", t["net_pct_2x"].mean() > 0), ("t ≥ 2", t_stat(t["net_pct"]) >= 2),
            ("both halves positive", t["net_pct"].iloc[:15].mean() > 0 and t["net_pct"].iloc[15:].mean() > 0),
            ("worst trade smaller than the average month", -t["net_rs"].min() < month)]


def track(name: str, ok: pd.DataFrame) -> list[str]:
    out = ["", f"## {name}: {len(ok)} trades booked"]
    if len(ok):
        x = ok["net_pct"]
        out += [f"- Mean {x.mean():+.1f} % (median {x.median():+.1f} %, t {t_stat(x):.2f}), won {(x > 0).mean() * 100:.0f} %, "
                f"total ₹{ok['net_rs'].sum():,.0f}; 2× charges {ok['net_pct_2x'].mean():+.1f} %",
                f"- Max up held: mean {ok['max_up_held_pct'].mean():+.0f} %, median {ok['max_up_held_pct'].median():+.0f} %; "
                f"≥ +100 % on {(ok['max_up_held_pct'] >= 100).sum()}"]
    if len(ok) >= GATE_N:
        ch = gate(ok)
        out += ["", f"Verdict: **{'PASS' if all(c for _, c in ch) else 'FAIL'}**", ""] + [f"- {'✔' if c else '✘'} {n}" for n, c in ch]
    else:
        out += [f"- Verdict: not yet ({len(ok)} of {GATE_N} trades)."]
    return out


def report(df: pd.DataFrame) -> list[str]:
    ok = df[df["skip"].fillna("") == ""] if len(df) else df
    out = [f"# S3 G1 forward · put held overnight, sold at the next open · from {START}", "",
           f"Pre-registered: `{PAGE}`. Bought at the real ask, sold at the real bid (1-second recorder), charges "
           f"from `server/charges.py`, {LOT} a lot. Each track's verdict at its {GATE_N}th trade.", "",
           f"Sessions in the store from {START}: {sum(1 for d in sessions() if d >= START)}"]
    out += track("G1 (every downside first breakout)", ok)
    out += track("G1-F (skips day-1 gap ≥ +0.3 %, range width 0.5-0.8 %, VIX ≥ 17)",
                 ok[ok["g1f_skip"].fillna("") == ""] if len(ok) else ok)
    if len(df):
        out += ["", "| Day | Signal | Strike | Paid (ask) | Sold (bid) | Exit | Net | Max up held | Next gap | G1-F |",
                "|---|---|---|---|---|---|---|---|---|---|"]
        for r in df.itertuples():
            f = "takes it" if not r.g1f_skip else f"skips: {r.g1f_skip}"
            if r.skip:
                out.append(f"| {r.day} | {r.signal} | | | | {r.skip} | | | | {f} |")
            else:
                out.append(f"| {r.day} | {r.signal} | {r.strike:.0f} | {r.paid:.2f} | {r.sold:.2f} | "
                           f"{r.exit_day} {r.exit_at} {r.reason} | {r.net_pct:+.1f} % | {r.max_up_held_pct:+.0f} % | "
                           f"{r.gap_pct:+.2f} % | {f} |")
    return out


def main():
    df = collect()
    df.to_csv(RES / "S3_G1_forward_trades.csv", index=False)
    lines = report(df)
    (RES / "S3_G1_forward.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
