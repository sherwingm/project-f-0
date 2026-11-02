"""S3 PUT1: NIFTY downside first breakout, puts only, on 2022-24 spot (strategies/S3_PUT1_downside_breakout_spot.md).

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_put1

Writes data/results/S3_PUT1_report.md and S3_PUT1_trades.csv. Run once.
"""
from __future__ import annotations

from datetime import timedelta

import pandas as pd

from index_data import load as L
from scanner import s3_regime as G
from scanner.s3_b2 import A_HALVES, A_WINDOW, HURDLE, exit_minute, signal
from scanner.s3_p1 import t_stat, vix_at
from scanner.s3_pods import RES

PAGE = "strategies/S3_PUT1_downside_breakout_spot.md"
PRIMARY, NEIGHBOURS, MIN_TRADES = 15, (12, 18), 150


def day_trade(g: pd.DataFrame, minutes: int, want: str, fail_exit: bool = False) -> dict | None:
    """The day's first breakout, if it is on the `want` side: entry = the minute after the signal's close, exit = the
    15:15 close (or the failure exit); move % in the option's direction."""
    sg = signal(g, minutes, None)
    if sg is None or sg[0] != want:
        return None
    side, ts, hi, lo = sg
    ent = ts + timedelta(minutes=1)
    ext = exit_minute(g, side, ent, hi, lo)[0] if fail_exit else ent.normalize() + timedelta(hours=15, minutes=15)
    px = g.set_index("timestamp")["close"]
    p0, p1 = px[px.index >= ent], px[px.index <= ext]
    if p0.empty or p1.empty:
        return None
    sgn = 1 if side == "CE" else -1
    return {"side": side, "signal": ts.strftime("%H:%M"), "entry": p0.index[0].strftime("%H:%M"),
            "exit": p1.index[-1].strftime("%H:%M"), "entry_px": p0.iloc[0], "exit_px": p1.iloc[-1],
            "move_pct": sgn * (p1.iloc[-1] / p0.iloc[0] - 1) * 100}


def collect(window=A_WINDOW) -> pd.DataFrame:
    sp = L.spot_1m(*window, "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    daily, rows, vc = G.daily(), [], {}
    for day, g in sp.groupby("d"):
        if len(g) < G.MIN_BARS:
            continue
        prev = daily[daily.index < day]
        down = bool(prev.iloc[-1]["close"] < prev.iloc[-1]["ema20"]) if len(prev) else None
        for name, o, want, fx in [("primary", PRIMARY, "PE", False), *((f"OR {n}", n, "PE", False) for n in NEIGHBOURS),
                                  ("calls (control)", PRIMARY, "CE", False), ("puts, failure exit", PRIMARY, "PE", True)]:
            t = day_trade(g, o, want, fx)
            if t:
                h, m = map(int, t["signal"].split(":"))
                rows.append({"day": day, "cell": name, **t, "trend_down": down,
                             "vix": vix_at(day, h, m, vc) if name == "primary" else None})
    return pd.DataFrame(rows)


def run() -> dict:
    allt = collect()
    p = allt[allt["cell"] == "primary"].copy()
    m, t = p["move_pct"].mean(), t_stat(p["move_pct"])
    halves = [p[(p["day"] >= a) & (p["day"] <= b)]["move_pct"] for a, b in A_HALVES]
    nb = {f"OR {n}": allt[allt["cell"] == f"OR {n}"]["move_pct"] for n in NEIGHBOURS}
    checks = [(f"at least {MIN_TRADES} trades", len(p) >= MIN_TRADES), (f"mean ≥ +{HURDLE:.2f} %", m >= HURDLE),
              ("t ≥ 2", t >= 2), ("both halves positive", all(h.mean() > 0 for h in halves)),
              ("neighbours OR 12 / 18 positive", all(x.mean() > 0 for x in nb.values()))]
    ok = all(c for _, c in checks)
    filt = p[(p["trend_down"] == True) & (p["vix"] < 14)]  # noqa: E712
    out = [f"# S3 PUT1 · NIFTY downside first breakout, puts only · spot {A_WINDOW[0]} → {A_WINDOW[1]}", "",
           f"Pre-registered: `{PAGE}`. Move = NIFTY's fall from the entry minute's close to the 15:15 close, in %. "
           f"Hurdle +{HURDLE:.2f} % a trade.", "", f"## Verdict: **{'PASS' if ok else 'FAIL'}**", ""]
    out += [f"- {'✔' if c else '✘'} {n}" for n, c in checks]
    out += ["", f"- Primary: {len(p)} trades, mean {m:+.3f} %, median {p['move_pct'].median():+.3f} %, t {t:.2f}, "
            f"fell after entry on {(p['move_pct'] > 0).mean() * 100:.0f} % of them.",
            "- Halves: " + " / ".join(f"{a} → {b}: {h.mean():+.3f} % ({len(h)})" for (a, b), h in zip(A_HALVES, halves)),
            "", "| Cell | Trades | Mean move | Median | t | In direction |", "|---|---|---|---|---|---|"]
    cells = [("primary (gate)", p["move_pct"]), *((f"{k} (gate)", v) for k, v in nb.items()),
             ("calls, same rules (control)", allt[allt["cell"] == "calls (control)"]["move_pct"]),
             ("puts + P4 filters (trend down, VIX < 14)", filt["move_pct"]),
             ("puts, failure exit", allt[allt["cell"] == "puts, failure exit"]["move_pct"])]
    for name, x in cells:
        out.append(f"| {name} | {len(x)} | {x.mean():+.3f} % | {x.median():+.3f} % | {t_stat(x):.2f} | "
                   f"{(x > 0).mean() * 100:.0f} % |")
    out += ["", "| Year | Trades | Mean move | t |", "|---|---|---|---|"]
    for y, x in p.groupby(pd.to_datetime(p["day"]).dt.year):
        out.append(f"| {y} | {len(x)} | {x['move_pct'].mean():+.3f} % | {t_stat(x['move_pct']):.2f} |")
    allt.to_csv(RES / "S3_PUT1_trades.csv", index=False)
    (RES / "S3_PUT1_report.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return {"pass": ok, "n": len(p), "mean": m, "t": t}


if __name__ == "__main__":
    run()
