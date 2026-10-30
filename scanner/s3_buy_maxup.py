"""S3 F4: max up of the buy pods' primary trades (strategies/S3_buy_followups_2026-10-30.md F4; descriptive only).

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_buy_maxup

For every primary trade in data/results/S3_{E1,Q1,B1,G1}_trades.csv: the highest combined value of the bought legs
after the entry minute, as % above the entry fills paid (gross), while held (to the exit minute) and any time (to
15:29 of the exit session). Marks follow scanner.s3_engine.simulate: each leg's last traded close carried forward; a
minute where any leg's mark is older than MARK_STALE minutes is not counted. Writes S3_F4_maxup_report.md + _trades.csv.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

import numpy as np
import pandas as pd

from index_data import load as L
from scanner.s3_engine import ENTRY_STALE, MARK_STALE, chain_between
from scanner.s3_pods import RES

PAGE = "strategies/S3_buy_followups_2026-10-30.md"
PRIMARY = {"E1": "E-1 → E 14:45", "Q1": "lookback 5 · pct 20 · hold 3",
           "B1": "OR 15 min · volume 2x · stop 25 %", "G1": "gap 0.5 % · confirm 15 min · stop 25 %"}
LEVELS = (10, 20, 50, 100)
LEG = re.compile(r"([BS])(\d+(?:\.\d+)?)(CE|PE)@([\d.]+)>([\d.]+)")


def entry_minute(pod: str, r) -> tuple[int, int]:
    if pod in ("E1", "Q1"):
        return 14, 45
    if pod == "B1":
        t = pd.Timestamp(f"2000-01-01 {r.signal}") + timedelta(minutes=1)
        return t.hour, t.minute
    return 9, 30                                   # G1 primary: confirmation after 15 minutes


def legs_of(s: str) -> list[tuple[str, float, str, float, float]]:
    return [(m[0], float(m[1]), m[2], float(m[3]), float(m[4])) for m in LEG.findall(s)]


def max_up(chain: pd.DataFrame, legs, t_in, t_exit, t_end) -> dict:
    """Max of the summed marks over (t_in, t_exit] and (t_in, t_end], in % above the summed entry fills."""
    w = chain[(chain["timestamp"] > t_in) & (chain["timestamp"] <= t_end)]
    minutes = pd.DatetimeIndex(sorted(w["timestamp"].unique()))
    paid = sum(fi for _, _, _, fi, _ in legs)
    if not len(minutes) or paid <= 0:
        return {"max_up_held_pct": np.nan, "max_up_any_pct": np.nan, "peak_held_at": None, "peak_any_at": None}
    val, stale = np.zeros(len(minutes)), np.zeros(len(minutes), bool)
    for side, k, opt, fi, _ in legs:
        g = w[(w["strike"] == k) & (w["option_type"] == opt)].drop_duplicates("timestamp", keep="last")
        ser = pd.Series(g["close"].to_numpy(float), index=pd.DatetimeIndex(g["timestamp"]))
        seen = pd.Series(ser.index, index=ser.index)
        px0 = L.price_at(chain, k, opt, t_in, stale=ENTRY_STALE)
        val += ser.reindex(minutes).ffill().fillna(px0 if px0 is not None else fi).to_numpy()
        sn = seen.reindex(minutes).ffill().fillna(t_in)
        stale |= (minutes - pd.DatetimeIndex(sn)).total_seconds() > MARK_STALE * 60
    up = np.where(~stale, (val / paid - 1) * 100, -np.inf)
    held = minutes <= t_exit
    out = {}
    for name, mask in (("held", held), ("any", np.ones(len(minutes), bool))):
        u = np.where(mask, up, -np.inf)
        i = int(np.argmax(u))
        ok = np.isfinite(u[i])
        out[f"max_up_{name}_pct"] = round(float(u[i]), 2) if ok else np.nan
        out[f"peak_{name}_at"] = minutes[i].strftime("%Y-%m-%d %H:%M") if ok else None
    return out


def run_pod(pod: str) -> pd.DataFrame:
    t = pd.read_csv(RES / f"S3_{pod}_trades.csv")
    t = t[(t["cell"] == PRIMARY[pod]) & (t["cost_mult"] == 1.0) & (t["skip"].fillna("") == "")].copy()
    rows = []
    for r in t.itertuples():
        day, exit_day, expiry = (date.fromisoformat(str(x)[:10]) for x in (r.day, r.exit_day, r.expiry))
        legs = legs_of(r.legs)
        hh, mm = entry_minute(pod, r)
        eh, em = (int(x) for x in str(r.exit_at).split(":"))
        chain = chain_between("NIFTY", expiry, day, exit_day)
        m = max_up(chain, legs, L.at(day, hh, mm), L.at(exit_day, eh, em), L.at(exit_day, 15, 29))
        paid = sum(fi for _, _, _, fi, _ in legs)
        booked = (sum(fo for *_, fo in legs) / paid - 1) * 100
        rows.append({"pod": pod, "day": day, "exit_day": exit_day, "entry": f"{hh:02d}:{mm:02d}", "exit_at": r.exit_at,
                     "reason": r.reason, "legs": r.legs, "booked_gross_pct": round(booked, 2),
                     "net_pct_premium": r.net_pct_premium, **m})
    return pd.DataFrame(rows)


def summary_lines(a: pd.DataFrame) -> list[str]:
    head = ("| Pod | Trades | Booked net (median) | Max up while held (median) | "
            + " | ".join(f"≥ +{x} % held / any" for x in LEVELS) + " | Max up any time (median) |")
    out = [head, "|" + "---|" * (5 + len(LEVELS))]
    for pod, g in a.groupby("pod", sort=False):
        lv = " | ".join(f"{(g['max_up_held_pct'] >= x).sum()} / {(g['max_up_any_pct'] >= x).sum()}" for x in LEVELS)
        out.append(f"| {pod} | {len(g)} | {g['net_pct_premium'].median():+.1f} % | {g['max_up_held_pct'].median():+.1f} % | "
                   f"{lv} | {g['max_up_any_pct'].median():+.1f} % |")
    return out


def main() -> None:
    a = pd.concat([run_pod(p) for p in PRIMARY], ignore_index=True)
    bad = a[a["max_up_held_pct"] + 0.01 < a["booked_gross_pct"]]
    lines = ["# S3 F4 · max up of the buy pods' primary trades (NIFTY, data-fix re-run)", "",
             f"Pre-registered: `{PAGE}` F4. Descriptive: no verdict, no exit is chosen from it. Max up = the highest "
             f"summed mark of the bought legs after the entry minute, in % above the entry fills paid (gross, no exit "
             f"costs); **held** = up to the exit minute, **any** = up to 15:29 of the exit session. Marks as the engine "
             f"(last close carried forward, stale after {MARK_STALE} min).", ""]
    lines += summary_lines(a)
    lines += ["", f"Check: max up while held below the booked gross on {len(bad)} of {len(a)} trades (should be 0: the "
              "exit mark is inside the held window and the exit fill is below the mark).", "",
              "Reading: a bought option that peaks at +50 % but is booked at a loss gave its gain back before the "
              "exit; a trade that never reached +10 % had nothing to take.", ""]
    for pod, g in a.groupby("pod", sort=False):
        lines += ["", f"## {pod}", "", "| day | entry | exit | reason | booked net | max up held | peak held at | max up any | peak any at |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for r in g.sort_values("day").itertuples():
            lines.append(f"| {r.day} | {r.entry} | {r.exit_day} {r.exit_at} | {r.reason} | {r.net_pct_premium:+.1f} % | "
                         f"{r.max_up_held_pct:+.1f} % | {r.peak_held_at} | {r.max_up_any_pct:+.1f} % | {r.peak_any_at} |")
    a.to_csv(RES / "S3_F4_maxup_trades.csv", index=False)
    (RES / "S3_F4_maxup_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:16]))


if __name__ == "__main__":
    main()
