"""S3 B2 optimisation (the user, 2026-11-04): 50 % stop, and hold the day's survivors overnight to see whether NIFTY
breaks out again the next day. In-sample on 2025-10-01 → 2026-10-30 (B2 was already run there), so a good number here
is a lead for a forward test only, never a pass.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_b2_hold

Day 1 is B2 unchanged (15-min opening range, breakout held 15 closes, ATM option of the nearest weekly with a session
left, exit the minute after a close back inside the range), except the stop. Variants:
  A  stop 25 %, out 15:15 (B2 as run)          B  stop 50 %, out 15:15
  C  stop 50 %, a trade still open at 15:15 is held to the next session's 15:15
  D  stop 50 %, held overnight, next session judged by its own breakout:
     - its own 15-min opening range (09:15-09:29); until 09:30 only the stop acts;
     - a close beyond the far edge (against the trade): out the next minute;
     - an accepted breakout our way (15 closes hold): held to 15:15, out the minute after a close back inside;
     - neither by 13:15: out 13:16.
The 50 % stop acts on every minute of both days (an opening gap through it fills at that minute's close).
Writes data/results/S3_B2_hold_report.md and _trades.csv.
"""
from __future__ import annotations

import sys
from datetime import date, time, timedelta

import pandas as pd

from index_data import load as L
from scanner import s3_regime as G
from scanner.s3_b2 import EXIT, LAST_ACCEPT, PRIMARY, exit_minute, signal
from scanner.s3_buy4 import U, expiry_after
from scanner.s3_buy_maxup import legs_of, max_up
from scanner.s3_engine import Leg, Spec, chain_between, run_day, spot_at
from scanner.s3_p1 import t_stat
from scanner.s3_pods import RES

WINDOW = (date(2025, 10, 1), date(2026, 10, 30))
HALVES = ((date(2025, 10, 1), date(2026, 3, 31)), (date(2026, 4, 1), date(2026, 10, 30)))
OR_MIN, ACCEPT = PRIMARY[0], PRIMARY[1]
VARIANTS = {"A": (0.25, "day"), "B": (0.50, "day"), "C": (0.50, "next 15:15"), "D": (0.50, "next breakout")}


def day2_exit(g2: pd.DataFrame, side: str):
    """(exit minute, reason, same-way accepted breakout?) on the next session, by its own opening range."""
    t = g2["timestamp"].dt.time
    rng = g2[(t >= time(9, 15)) & (t < time(9, 30))]
    rest = g2[(t >= time(9, 30)) & (t < EXIT)]
    day = g2["timestamp"].iloc[0].normalize()
    if rng.empty or rest.empty:
        return day + timedelta(hours=15, minutes=15), "d2 time", False
    hi, lo = float(rng["high"].max()), float(rng["low"].min())
    against = (rest["close"] < lo) if side == "CE" else (rest["close"] > hi)
    t_against = rest.loc[against.idxmax(), "timestamp"] if against.any() else None
    sg = signal(g2, OR_MIN, ACCEPT)
    ours = sg is not None and sg[0] == side
    if ours and (t_against is None or sg[1] < t_against):
        ext, why = exit_minute(g2, side, sg[1] + timedelta(minutes=1), sg[2], sg[3])
        return ext, ("d2 fail" if why == "fail" else "d2 time"), True
    if t_against is not None and (t_against.time() <= LAST_ACCEPT):
        return t_against + timedelta(minutes=1), "d2 against", ours
    return day + timedelta(hours=13, minutes=16), "d2 none", ours


def trade(day, g, g2, nxt, e, sg, stop, hold, dte) -> dict:
    side, ts, hi, lo = sg
    ent = ts + timedelta(minutes=1)
    ext, why = exit_minute(g, side, ent, hi, lo)
    exit_day, d2_ours = None, None
    if why == "time" and hold != "day":
        if nxt is None or g2 is None or nxt > e:
            return {"day": day, "skip": "no next session"}
        exit_day = nxt
        if hold == "next 15:15":
            ext, why = L.at(nxt, 15, 15), "d2 time"
        else:
            ext, why, d2_ours = day2_exit(g2, side)
    s = spot_at(day, ent.hour, ent.minute, U["index"])
    if s is None:
        return {"day": day, "skip": "no spot at entry"}
    k = round(float(g.loc[g["timestamp"] == ts, "close"].iloc[0]) / U["step"]) * U["step"]
    off = int(round((k - round(s / U["step"]) * U["step"]) / U["step"]))
    sp = Spec("B2 hold", [Leg("BUY", side, off)], entry=(ent.hour, ent.minute), exit=(ext.hour, ext.minute), stop=stop)
    r = run_day(sp, day, e, underlying=U["underlying"], index=U["index"], exit_day=exit_day, lot=U["lot"])
    if r.get("skip"):
        return r
    if r["reason"] == "time":
        r["reason"] = why
    ch = chain_between(U["underlying"], e, day, exit_day)
    t_in, t_out = L.at(day, ent.hour, ent.minute), L.at(exit_day or day, ext.hour, ext.minute)
    if r["reason"] == "stop":
        t_out = L.at(r["exit_day"], *map(int, r["exit_at"].split(":")))
    mu = max_up(ch, legs_of(r["legs"]), t_in, t_out, t_out)
    return {**r, "side": side, "signal": ts.strftime("%H:%M"), "expiry": e, "dte": dte, "held_over": exit_day is not None,
            "d2_ours": d2_ours, "max_up_pct": mu["max_up_held_pct"]}


def collect() -> pd.DataFrame:
    sp = L.spot_1m(WINDOW[0], WINDOW[1] + timedelta(days=10), U["index"])
    sp["d"] = sp["timestamp"].dt.date
    days = {d: g for d, g in sp.groupby("d") if len(g) >= G.MIN_BARS}
    ses = sorted(days)
    rows = []
    for i, day in enumerate(ses):
        if not WINDOW[0] <= day <= WINDOW[1]:
            continue
        e = expiry_after(day)
        if e is None:
            continue
        sg = signal(days[day], OR_MIN, ACCEPT)
        if sg is None:
            continue
        nxt = ses[i + 1] if i + 1 < len(ses) else None
        dte = sum(1 for d in ses if day < d <= e)
        for v, (stop, hold) in VARIANTS.items():
            r = trade(day, days[day], days.get(nxt), nxt, e, sg, stop, hold, dte)
            rows.append({**r, "variant": v, "day": day})
    return pd.DataFrame(rows)


HEAD = ["| Group | Trades | Mean net | Median | t | Won | Max up mean | Max up median | ≥ +50 % | ≥ +100 % | Total ₹ |",
        "|---|---|---|---|---|---|---|---|---|---|---|"]


def line(name, g) -> str:
    if g.empty:
        return f"| {name} | 0 | | | | | | | | | |"
    n, m = g["net_pct_premium"], g["max_up_pct"]
    return (f"| {name} | {len(g)} | {n.mean():+.1f} % | {n.median():+.1f} % | {t_stat(n):.2f} | {(n > 0).mean() * 100:.0f} % | "
            f"{m.mean():+.0f} % | {m.median():+.0f} % | {(m >= 50).mean() * 100:.0f} % | {(m >= 100).mean() * 100:.0f} % | "
            f"{g['net_rs'].sum():,.0f} |")


def report(df: pd.DataFrame) -> list[str]:
    ok = df[df["skip"].fillna("") == ""].copy()
    dd = pd.to_datetime(ok["day"]).dt.date
    names = {"A": "A · stop 25 %, out 15:15 (B2)", "B": "B · stop 50 %, out 15:15",
             "C": "C · stop 50 %, survivors held to next day 15:15", "D": "D · stop 50 %, next day judged by its breakout"}
    out = [f"# S3 B2 optimisation · 50 % stop and overnight hold · {WINDOW[0]} → {WINDOW[1]}", "",
           "**In-sample:** B2 was already run on this window, so nothing here is a pass. Net after slippage and "
           "charges, % of the premium, 1 lot. Max up = the best value while held, % above the price paid.", "",
           "## The four variants", "", *HEAD]
    out += [line(names[v], ok[ok["variant"] == v]) for v in VARIANTS]
    out += ["", "## Halves", "", *HEAD]
    for v in VARIANTS:
        for a, b in HALVES:
            out.append(line(f"{v} · {a} → {b}", ok[(ok["variant"] == v) & (dd >= a) & (dd <= b)]))
    out += ["", "## By exit", "", *HEAD]
    for v in VARIANTS:
        g = ok[ok["variant"] == v]
        out += [line(f"{v} · {r}", x) for r, x in g.groupby("reason")]
    out += ["", "## Trades held overnight only", "", *HEAD]
    for v in ("C", "D"):
        g = ok[(ok["variant"] == v) & ok["held_over"]]
        out.append(line(f"{v} · all held", g))
        if v == "D":
            out += [line(f"D · next day broke out our way: {k}", x) for k, x in g.groupby("d2_ours")]
    c, b = ok[ok["variant"] == "C"].set_index("day"), ok[ok["variant"] == "B"].set_index("day")
    over = c[c["held_over"]].index
    if len(over):
        out += ["", f"Same {len(over)} trades sold at day 1's 15:15 (B): {b.loc[b.index.intersection(over), 'net_pct_premium'].mean():+.1f} %; "
                f"held to day 2's 15:15 (C): {c.loc[over, 'net_pct_premium'].mean():+.1f} %."]
    out += ["", "## By days to expiry at entry (sessions left)", "", *HEAD]
    band = lambda x: "4+" if x >= 4 else str(int(x))
    for v in VARIANTS:
        g = ok[ok["variant"] == v]
        out += [line(f"{v} · DTE {k}", x) for k, x in g.groupby(g["dte"].map(band))]
    sk = df[df["skip"].fillna("") != ""]
    out += ["", f"Skipped: {len(sk)} ({sk.groupby('variant')['skip'].value_counts().to_dict()})"]
    return out


def main():
    df = collect()
    df.to_csv(RES / "S3_B2_hold_trades.csv", index=False)
    lines = report(df)
    (RES / "S3_B2_hold_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
