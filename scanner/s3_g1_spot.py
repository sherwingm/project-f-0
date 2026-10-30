"""S3 F3a: does a confirmed up gap follow through more than a down gap? NIFTY 50 spot, 2022-01-03 → 2024-09-30, a
window G1 never used (strategies/S3_buy_followups_2026-10-30.md F3a; G1's signal from scanner.s3_buy4.g1_signal).

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_g1_spot

Writes data/results/S3_F3a_gap_spot_report.md and S3_F3a_gap_spot_signals.csv. Spot moves only: it cannot price an
option, so a pass only makes a forward paper test worth proposing.
"""
from __future__ import annotations

from datetime import date, time

import numpy as np
import pandas as pd

from index_data import load as L
from scanner import s3_regime as G
from scanner.s3_buy4 import g1_signal
from scanner.s3_p1 import t_stat
from scanner.s3_pods import RES

WINDOW = (date(2022, 1, 3), date(2024, 9, 30))
HALVES = ((date(2022, 1, 3), date(2023, 5, 31)), (date(2023, 6, 1), date(2024, 9, 30)))
GAP, CONFIRM, EXIT = 0.5, 15, time(15, 15)
PAGE = "strategies/S3_buy_followups_2026-10-30.md"


def welch_t(a: pd.Series, b: pd.Series) -> float:
    a, b = pd.Series(a, dtype=float).dropna(), pd.Series(b, dtype=float).dropna()
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return float((a.mean() - b.mean()) / se) if se > 0 else float("nan")


def outcome(g: pd.DataFrame, ent: pd.Timestamp, sign: int) -> dict | None:
    """Moves in % of the entry close (the bar at `ent`), signed by `sign` (+1 up gap, -1 down gap)."""
    t = g["timestamp"]
    at = g[t == ent]
    end = g[t.dt.time == EXIT]
    after = g[(t > ent) & (t.dt.time <= EXIT)]
    if at.empty or end.empty or after.empty:
        return None
    e = float(at["close"].iloc[0])
    fav = (after["high"].max() / e - 1) * 100 if sign > 0 else (1 - after["low"].min() / e) * 100
    adv = (after["low"].min() / e - 1) * 100 if sign > 0 else (1 - after["high"].max() / e) * 100
    return {"entry": e, "exit_1515": float(end["close"].iloc[0]),
            "follow_pct": sign * (float(end["close"].iloc[0]) / e - 1) * 100, "max_fav_pct": fav, "max_adv_pct": adv}


def collect() -> tuple[pd.DataFrame, pd.DataFrame]:
    daily = G.daily("NIFTY50")
    sp = L.spot_1m(*WINDOW, "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    sig, base = [], []
    for day, g in sp.groupby("d"):
        if len(g) < G.MIN_BARS or not WINDOW[0] <= day <= WINDOW[1]:
            continue
        g = g.reset_index(drop=True)
        o = outcome(g, pd.Timestamp(L.at(day, 9, 30)), 1)
        if o is not None:
            base.append({"day": day, "move_pct": o["follow_pct"]})
        prev = daily[daily.index < day]
        if prev.empty:
            continue
        s = g1_signal(g, float(prev["close"].iloc[-1]), GAP, CONFIRM)
        if s is None:
            continue
        side, ent, gap = s
        o = outcome(g, ent, 1 if side == "CE" else -1)
        if o is None:
            continue
        sig.append({"day": day, "side": "up" if side == "CE" else "down", "gap_pct": round(gap, 3),
                    "entry_time": ent.strftime("%H:%M"), **{k: round(v, 4) for k, v in o.items()}})
    return pd.DataFrame(sig), pd.DataFrame(base)


def verdict(sig: pd.DataFrame, base: pd.DataFrame) -> dict:
    up, dn = sig[sig["side"] == "up"]["follow_pct"], sig[sig["side"] == "down"]["follow_pct"]
    halves = [sig[(sig["side"] == "up") & (sig["day"] >= a) & (sig["day"] <= b)]["follow_pct"] for a, b in HALVES]
    checks = {
        "1 up-gap follow-through > 0, t >= 2": bool(len(up) and up.mean() > 0 and t_stat(up) >= 2),
        "2 beats every session's 09:30 → 15:15 move (Welch t >= 2)": bool(welch_t(up, base["move_pct"]) >= 2),
        "3 beats the down-gap follow-through (Welch t >= 2)": bool(welch_t(up, dn) >= 2),
        "4 positive in both halves": bool(all(len(h) and h.mean() > 0 for h in halves)),
    }
    return {"checks": checks, "supported": all(checks.values()), "halves": halves}


def _row(name: str, x: pd.Series) -> str:
    x = pd.Series(x, dtype=float)
    return (f"| {name} | {len(x)} | {x.mean():+.3f} % | {x.median():+.3f} % | {t_stat(x):.2f} | "
            f"{(x > 0).mean() * 100:.0f} % |")


def main() -> None:
    sig, base = collect()
    v = verdict(sig, base)
    up, dn = sig[sig["side"] == "up"], sig[sig["side"] == "down"]
    out = [f"# S3 F3a · NIFTY 50 gap follow-through on spot, {WINDOW[0]} → {WINDOW[1]}", "",
           f"Pre-registered: `{PAGE}` F3a. Signal `scanner.s3_buy4.g1_signal` (gap ≥ {GAP} % vs the previous session's "
           f"last close, confirmed by the 09:29 close, entry at the 09:30 close); moves in % of the spot, signed in the "
           f"gap's direction; exit 15:15. Spot store 62a23257 (09:15 opens = NSE's official). Spot only: no option "
           f"prices, decay or costs.", "",
           f"**Verdict: the hint is {'SUPPORTED' if v['supported'] else 'NOT supported'}.**", ""]
    out += [f"- {k}: {'yes' if ok else 'no'}" for k, ok in v["checks"].items()]
    out += ["", "| Group | n | Mean | Median | t | Share > 0 |", "|---|---|---|---|---|---|",
            _row("Up gaps, follow-through to 15:15", up["follow_pct"]),
            _row("Down gaps, follow-through to 15:15", dn["follow_pct"]),
            _row("Every session, 09:30 → 15:15 (unsigned)", base["move_pct"]),
            _row(f"Up gaps, half 1 ({HALVES[0][0]} → {HALVES[0][1]})", v["halves"][0]),
            _row(f"Up gaps, half 2 ({HALVES[1][0]} → {HALVES[1][1]})", v["halves"][1]), "",
            f"Welch t: up vs every session {welch_t(up['follow_pct'], base['move_pct']):.2f}; up vs down "
            f"{welch_t(up['follow_pct'], dn['follow_pct']):.2f}.", "",
            "| Side | Max favourable 09:31-15:15 (median) | Share ≥ 0.25 % | Share ≥ 0.5 % | Max adverse (median) |",
            "|---|---|---|---|---|"]
    for name, g in (("up", up), ("down", dn)):
        out.append(f"| {name} | {g['max_fav_pct'].median():+.3f} % | {(g['max_fav_pct'] >= 0.25).mean() * 100:.0f} % | "
                   f"{(g['max_fav_pct'] >= 0.5).mean() * 100:.0f} % | {g['max_adv_pct'].median():+.3f} % |")
    out += ["", "## Signals", "", "| day | side | gap % | follow % | max fav % | max adv % |", "|---|---|---|---|---|---|"]
    for r in sig.sort_values("day").itertuples():
        out.append(f"| {r.day} | {r.side} | {r.gap_pct:+.2f} | {r.follow_pct:+.3f} | {r.max_fav_pct:+.3f} | {r.max_adv_pct:+.3f} |")
    RES.mkdir(parents=True, exist_ok=True)
    sig.to_csv(RES / "S3_F3a_gap_spot_signals.csv", index=False)
    (RES / "S3_F3a_gap_spot_report.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out[:20]))


if __name__ == "__main__":
    main()
