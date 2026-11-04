"""S3 PUT1 with B2's optimisation rules (the user, 2026-11-04: "try applying the rule i have said for b2
optimization"): 50 % stop, and hold overnight to see whether NIFTY breaks down again the next day. Descriptive /
in-sample: PUT1's puts were already priced on these option minutes (scripts/s3_put1_options.py).

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_put1_hold

Day 1 is PUT1 unchanged: 09:15-09:29 range, the first close outside it 09:30-13:00, trade only when it is below the
low, ATM put of the nearest weekly with a session left, bought the next minute. PUT1 has no fail exit. Variants:
  P0  no stop, out 15:15 (PUT1 as priced)       P1  50 % stop, out 15:15
  P2  50 % stop, held to the next session's 15:15
  P3  50 % stop, held overnight, the next session judged by PUT1's own rule:
      its first breakout down → held to 15:15; its first breakout up → out the next minute; none by 13:00 → out 13:16.
The stop acts on every minute of both days (an opening gap through it fills at that minute's close).
Years are reported apart: 2024-10 → 2025-09 and 2025-10 → 2026-10.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta

import pandas as pd

from index_data import load as L
from scanner import s3_regime as G
from scanner.s3_b2 import signal
from scanner.s3_b2_hold import HEAD, line
from scanner.s3_buy4 import expiry_after
from scanner.s3_buy_maxup import legs_of, max_up
from scanner.s3_engine import Leg, Spec, chain_between, run_day
from scanner.s3_pods import RES

WINDOW = (date(2024, 10, 1), date(2026, 10, 28))
YEARS = ((date(2024, 10, 1), date(2025, 9, 30)), (date(2025, 10, 1), date(2026, 10, 28)))
VARIANTS = {"P0": (None, "day"), "P1": (0.50, "day"), "P2": (0.50, "next 15:15"), "P3": (0.50, "next breakout"),
            "G1": (0.50, "next open"), "G2": (0.50, "gap down hold"), "G3": (0.50, "gap down sell")}
# G (the user, 2026-11-04: "why dont we use the gift nifty to check whether to hold or sell"). No GIFT Nifty history
# is stored; the next day's opening gap (09:15 open against day 1's last close) is what GIFT Nifty shows by 09:00,
# so it stands in for it. Every G trade is held overnight; at the next open:
#   G1 sell at 09:16 whatever the gap      G2 gap down (our way): keep by P3's rule; gap up: sell 09:16
#   G3 gap down: sell 09:16 (bank it); gap up: keep by P3's rule
NAMES = {"P0": "P0 · no stop, out 15:15 (PUT1)", "P1": "P1 · stop 50 %, out 15:15",
         "P2": "P2 · stop 50 %, held to next day 15:15", "P3": "P3 · stop 50 %, next day judged by its breakout",
         "G1": "G1 · held overnight, sold at next open", "G2": "G2 · gap down: keep (P3), gap up: sell at open",
         "G3": "G3 · gap down: sell at open, gap up: keep (P3)"}


def day2_exit(g2: pd.DataFrame):
    """(exit minute, reason, broke down again?) on the next session by PUT1's rule."""
    sg = signal(g2, 15, None)
    day = g2["timestamp"].iloc[0].normalize()
    if sg is None:
        return day + timedelta(hours=13, minutes=16), "d2 none", False
    if sg[0] == "PE":
        return day + timedelta(hours=15, minutes=15), "d2 down", True
    return sg[1] + timedelta(minutes=1), "d2 up", False


def trade(day, nxt, g2, e, ent, stop, hold, dte, gap=None) -> dict:
    exit_day, ext, why, again = None, L.at(day, 15, 15), "time", None
    if hold != "day":
        if nxt is None or g2 is None or nxt > e:
            return {"day": day, "skip": "no next session"}
        exit_day = nxt
        if hold == "next 15:15":
            ext, why = L.at(nxt, 15, 15), "d2 time"
        elif hold == "next open" or (hold == "gap down hold" and gap >= 0) or (hold == "gap down sell" and gap < 0):
            ext, why = L.at(nxt, 9, 16), "d2 open"
        else:
            ext, why, again = day2_exit(g2)
    sp = Spec("PUT1 hold", [Leg("BUY", "PE", 0)], entry=(ent.hour, ent.minute), exit=(ext.hour, ext.minute), stop=stop)
    r = run_day(sp, day, e, exit_day=exit_day)
    if r.get("skip"):
        return r
    if r["reason"] == "time":
        r["reason"] = why
    t_in = L.at(day, ent.hour, ent.minute)
    t_out = L.at(r["exit_day"], *map(int, r["exit_at"].split(":")))
    mu = max_up(chain_between("NIFTY", e, day, exit_day), legs_of(r["legs"]), t_in, t_out, t_out)
    return {**r, "expiry": e, "dte": dte, "entry": ent.strftime("%H:%M"), "held_over": exit_day is not None and
            r["exit_day"] != day, "d2_down": again, "max_up_pct": mu["max_up_held_pct"]}


def collect() -> pd.DataFrame:
    sp = L.spot_1m(WINDOW[0], WINDOW[1] + timedelta(days=10), "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    days = {d: g for d, g in sp.groupby("d") if len(g) >= G.MIN_BARS}
    ses = sorted(days)
    rows = []
    for i, day in enumerate(ses):
        if not WINDOW[0] <= day <= WINDOW[1]:
            continue
        sg = signal(days[day], 15, None)
        if sg is None or sg[0] != "PE":
            continue
        e = expiry_after(day)
        if e is None:
            continue
        nxt = ses[i + 1] if i + 1 < len(ses) else None
        dte = sum(1 for d in ses if day < d <= e)
        g2 = days.get(nxt)
        gap = (float(g2["open"].iloc[0]) / float(days[day]["close"].iloc[-1]) - 1) * 100 if g2 is not None else None
        for v, (stop, hold) in VARIANTS.items():
            rows.append({**trade(day, nxt, g2, e, sg[1] + timedelta(minutes=1), stop, hold, dte, gap),
                         "variant": v, "day": day, "gap_pct": gap})
    return pd.DataFrame(rows)


def report(df: pd.DataFrame) -> list[str]:
    ok = df[df["skip"].fillna("") == ""].copy()
    dd = pd.to_datetime(ok["day"]).dt.date
    out = [f"# S3 PUT1 with B2's rules · 50 % stop and overnight hold · {WINDOW[0]} → {WINDOW[1]}", "",
           "**In-sample / descriptive:** PUT1's puts were already priced on these minutes. Net after slippage and "
           "charges, % of the premium, 1 lot. Max up = the best minute close while held, % above the price paid.", "",
           "## The four variants", "", *HEAD]
    out += [line(NAMES[v], ok[ok["variant"] == v]) for v in VARIANTS]
    out += ["", "## By year", "", *HEAD]
    for v in VARIANTS:
        out += [line(f"{v} · {a} → {b}", ok[(ok["variant"] == v) & (dd >= a) & (dd <= b)]) for a, b in YEARS]
    out += ["", "## By exit", "", *HEAD]
    for v in VARIANTS:
        g = ok[ok["variant"] == v]
        out += [line(f"{v} · {r}", x) for r, x in g.groupby("reason")]
    p3 = ok[(ok["variant"] == "P3") & ok["held_over"]]
    out += ["", "## P3 trades held overnight, by what the next day did (known only afterwards)", "", *HEAD]
    out += [line(f"next day broke down again: {k}", x) for k, x in p3.groupby("d2_down")]
    p1 = ok[ok["variant"] == "P1"].set_index("day")
    if len(p3):
        same = p1.loc[p1.index.intersection(p3["day"]), "net_pct_premium"]
        out += ["", f"The same {len(same)} trades sold at day 1's 15:15 (P1): {same.mean():+.1f} %; held by P3's rule: "
                f"{p3['net_pct_premium'].mean():+.1f} %."]
    g1 = ok[(ok["variant"] == "G1") & ok["held_over"]]
    out += ["", "## Held overnight, by the next day's opening gap (what GIFT Nifty would show)", "", *HEAD]
    for v in ("G1", "P3"):
        x = ok[(ok["variant"] == v) & ok["day"].isin(g1["day"])]
        out += [line(f"{v} · gap {'down (our way)' if k else 'up / flat'}", y) for k, y in x.groupby(x["gap_pct"] < 0)]
    out += ["", "## By days to expiry at entry (sessions left)", "", *HEAD]
    band = lambda x: "4+" if x >= 4 else str(int(x))
    for v in VARIANTS:
        g = ok[ok["variant"] == v]
        out += [line(f"{v} · DTE {k}", x) for k, x in g.groupby(g["dte"].map(band))]
    sk = df[df["skip"].fillna("") != ""]
    out += ["", f"Skipped: {len(sk)} rows ({sk['skip'].str.split(' at ').str[0].value_counts().to_dict()})"]
    return out


def main():
    df = collect()
    df.to_csv(RES / "S3_PUT1_hold_trades.csv", index=False)
    lines = report(df)
    (RES / "S3_PUT1_hold_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
