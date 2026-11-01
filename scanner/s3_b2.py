"""S3 B2: NIFTY opening-range breakout that holds ("accepted"), long ATM option (strategies/S3_B2_accepted_breakout.md).

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_b2 [B] [A]

B: options, 2024-10-01 → 2026-10-28, the S3 gate (halves = the user's two periods). Writes S3_B2_report.md / _trades.csv.
A: NIFTY 50 spot only, 2022-01-03 → 2024-09-30 (no option prices there): the directional spot move entry → exit
   against the +0.10 % hurdle. Writes S3_B2_stageA_report.md / _trades.csv.
Run order (the user, 2026-11-01): B first, then A; B2 goes on to the forward stage only if both pass.
"""
from __future__ import annotations

import sys
from datetime import date, time, timedelta

import numpy as np
import pandas as pd

from index_data import load as L
from scanner import s3_regime as G
from scanner.s3_buy4 import HALVES, U, WINDOW, _directional_side, _note, _pod, _run, expiry_after
from scanner.s3_engine import Leg, Spec, spot_at
from scanner.s3_p1 import t_stat, vix_at
from scanner.s3_pods import RES, write_report

PAGE = "strategies/S3_B2_accepted_breakout.md"
PRIMARY = (15, 15, 0.25)                    # opening range minutes, acceptance closes, stop
NEIGHBOURS = [(15, 10, 0.25), (15, 20, 0.25), (12, 15, 0.25), (18, 15, 0.25), (15, 15, 0.20), (15, 15, 0.30)]
LAST_BREAKOUT, LAST_ACCEPT, EXIT = time(13, 0), time(13, 15), time(15, 15)
A_WINDOW = (date(2022, 1, 3), date(2024, 9, 30))
A_HALVES = ((date(2022, 1, 3), date(2023, 5, 31)), (date(2023, 6, 1), date(2024, 9, 30)))
HURDLE, A_MIN_TRADES = 0.10, 150


def label(c) -> str:
    o, a, s = c
    return f"OR {o} min · accept {'none' if a is None else f'{a} closes'} · stop {int(round(s * 100))} %"


def signal(day_spot: pd.DataFrame, minutes: int, accept: int | None):
    """(side, signal minute, range high, range low) of the first breakout (a close beyond the range, end of range →
    13:00) whose next `accept` closes all stay beyond that edge; the signal minute is the last of them (≤ 13:15).
    A breakout that closes back inside first is void and the scan goes on. `accept` None: the first breakout."""
    t1 = (pd.Timestamp("2000-01-01 09:15") + pd.Timedelta(minutes=minutes)).time()
    t = day_spot["timestamp"].dt.time
    rng = day_spot[(t >= time(9, 15)) & (t < t1)]
    rest = day_spot[t >= t1].reset_index(drop=True)
    if rng.empty or rest.empty:
        return None
    hi, lo = float(rng["high"].max()), float(rng["low"].min())
    closes, ts = rest["close"].to_numpy(float), list(rest["timestamp"])
    i = 0
    while i < len(rest) and ts[i].time() <= LAST_BREAKOUT:
        c = closes[i]
        side = "CE" if c > hi else ("PE" if c < lo else None)
        if side is None:
            i += 1
            continue
        if accept is None:
            return side, ts[i], hi, lo
        if i + accept >= len(rest):
            return None
        nxt = closes[i + 1:i + 1 + accept]
        held = (nxt >= hi) if side == "CE" else (nxt <= lo)
        if held.all():
            return (side, ts[i + accept], hi, lo) if ts[i + accept].time() <= LAST_ACCEPT else None
        i = i + 1 + int(np.argmin(held))      # the first close back inside; scanning goes on after it
    return None


def exit_minute(day_spot: pd.DataFrame, side: str, entry: pd.Timestamp, hi: float, lo: float):
    """(exit minute, reason): the minute after the first close back inside the range from the entry minute on
    ('fail'), else 15:15 ('time')."""
    d = day_spot[(day_spot["timestamp"] >= entry) & (day_spot["timestamp"].dt.time < EXIT)]
    back = (d["close"] < hi) if side == "CE" else (d["close"] > lo)
    if back.any():
        return d.loc[back.idxmax(), "timestamp"] + timedelta(minutes=1), "fail"
    return entry.normalize() + timedelta(hours=15, minutes=15), "time"


def _long(name, day, expiry, side, k_signal, ent, ext, stop, cm) -> dict:
    s = spot_at(day, ent.hour, ent.minute, U["index"])
    if s is None:
        return {"day": day, "skip": "no spot at entry"}
    st = U["step"]
    off = int(round((k_signal - round(s / st) * st) / st))
    sp = Spec(name, [Leg("BUY", side, off)], entry=(ent.hour, ent.minute), exit=(ext.hour, ext.minute), stop=stop,
              cost_mult=cm)
    return _run(sp, day, expiry)


def run_b() -> dict:
    sp = L.spot_1m(*WINDOW, U["index"])
    sp["d"] = sp["timestamp"].dt.date
    rows, n, vc = [], 0, {}
    cells = [PRIMARY] + NEIGHBOURS
    for day, g in sp.groupby("d"):
        if len(g) < G.MIN_BARS:
            continue
        n += 1
        e = expiry_after(day)
        sigs = {}
        for cell, cm in [(c, 1.0) for c in cells] + [(PRIMARY, 2.0)]:
            o, a, stop = cell
            base = {"day": day, "cell": label(cell), "cost_mult": cm, "event": False, "weekday": day.strftime("%a"),
                    "expiry": e}
            if e is None:
                rows.append({**base, "skip": "no expiry"})
                continue
            if (o, a) not in sigs:
                sigs[(o, a)] = signal(g, o, a)
            sg = sigs[(o, a)]
            if sg is None:
                rows.append({**base, "skip": "no confirmed breakout"})
                continue
            side, ts, hi, lo = sg
            ent = ts + timedelta(minutes=1)
            ext, why = exit_minute(g, side, ent, hi, lo)
            k = round(float(g.loc[g["timestamp"] == ts, "close"].iloc[0]) / U["step"]) * U["step"]
            r = _long(label(cell), day, e, side, k, ent, ext, stop, cm)
            if r.get("reason") == "time" and why == "fail":
                r["reason"] = "fail"                # the engine's planned exit minute was the failure exit
            rows.append({**r, **base, "side": side, "signal": ts.strftime("%H:%M"),
                         "vix": vix_at(day, ts.hour, ts.minute, vc)})
    allt = pd.DataFrame(rows)
    pod = _pod("B2", "accepted 15-min opening-range breakout (15 closes hold), long ATM, exit when it fails / 25 % stop / 15:15",
               PAGE, cells=cells, spec=None, primary=PRIMARY, neighbours=NEIGHBOURS, label=label, skip_events=False,
               measure="premium")
    extra = _note() + _directional_side(allt, label(PRIMARY), "-", "not run for B2")
    allt = allt[allt["skip"].fillna("") != "no confirmed breakout"].copy()
    return write_report(pod, allt, n, WINDOW, HALVES, False, extra=extra)


def spot_trades(window, cell) -> pd.DataFrame:
    """Stage A: per session, the directional NIFTY move entry close → exit close (%), exits 'fail' / 'time'."""
    o, a, _ = cell
    sp = L.spot_1m(*window, "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    rows = []
    for day, g in sp.groupby("d"):
        if len(g) < G.MIN_BARS:
            continue
        sg = signal(g, o, a)
        if sg is None:
            continue
        side, ts, hi, lo = sg
        ent = ts + timedelta(minutes=1)
        ext, why = exit_minute(g, side, ent, hi, lo)
        px = g.set_index("timestamp")["close"]
        p0 = px[px.index >= ent]
        p1 = px[px.index <= ext]
        if p0.empty or p1.empty:
            continue
        sgn = 1 if side == "CE" else -1
        rows.append({"day": day, "side": side, "signal": ts.strftime("%H:%M"), "entry": p0.index[0].strftime("%H:%M"),
                     "exit": p1.index[-1].strftime("%H:%M"), "reason": why, "entry_px": p0.iloc[0],
                     "exit_px": p1.iloc[-1], "move_pct": sgn * (p1.iloc[-1] / p0.iloc[0] - 1) * 100})
    return pd.DataFrame(rows)


def run_a() -> dict:
    p = spot_trades(A_WINDOW, PRIMARY)
    nb = {label(c): spot_trades(A_WINDOW, c) for c in [(15, 10, 0.25), (15, 20, 0.25)]}
    base = spot_trades(A_WINDOW, (15, None, 0.25))
    m, t = p["move_pct"].mean(), t_stat(p["move_pct"])
    halves = [p[(p["day"] >= a) & (p["day"] <= b)]["move_pct"] for a, b in A_HALVES]
    checks = [(f"at least {A_MIN_TRADES} trades", len(p) >= A_MIN_TRADES),
              (f"mean ≥ +{HURDLE:.2f} %", m >= HURDLE), ("t ≥ 2", t >= 2),
              ("each half positive", all(h.mean() > 0 for h in halves)),
              ("acceptance 10 and 20 neighbours positive", all(x["move_pct"].mean() > 0 for x in nb.values()))]
    ok = all(c for _, c in checks)
    L_ = [f"# S3 B2 stage A · NIFTY 50 spot, {A_WINDOW[0]} → {A_WINDOW[1]} (the window the idea has not seen)", "",
          f"Pre-registered: `{PAGE}`. Spot only: the move of NIFTY in the trade's direction from the entry minute's "
          f"close to the exit minute's close (the minute after the first close back inside the range, else 15:15). "
          f"Hurdle +{HURDLE:.2f} % a trade (costs and decay of the option, from B1's trades).", "",
          f"## Verdict: **{'PASS' if ok else 'FAIL'}**", ""]
    L_ += [f"- {'✔' if c else '✘'} {n}" for n, c in checks]
    L_ += ["", f"- Trades {len(p)} of {p['day'].nunique() if len(p) else 0} signal days; mean {m:+.3f} %, median "
           f"{p['move_pct'].median():+.3f} %, t {t:.2f}; in the direction {(p['move_pct'] > 0).mean() * 100:.0f} %.",
           f"- Halves: " + " / ".join(f"{a} → {b}: {h.mean():+.3f} % ({len(h)})" for (a, b), h in zip(A_HALVES, halves)),
           "", "| Cell | Trades | Mean move | t | In direction |", "|---|---|---|---|---|"]
    for name, x in [(label(PRIMARY), p), *nb.items(), ("first breakout, no acceptance (B1's signal), same exits", base)]:
        L_.append(f"| {name} | {len(x)} | {x['move_pct'].mean():+.3f} % | {t_stat(x['move_pct']):.2f} | "
                  f"{(x['move_pct'] > 0).mean() * 100:.0f} % |")
    L_ += ["", "| Group | Trades | Mean move | t |", "|---|---|---|---|"]
    for k, x in [*p.groupby("side"), *p.groupby("reason"), *p.groupby(pd.to_datetime(p["day"]).dt.year)]:
        L_.append(f"| {k} | {len(x)} | {x['move_pct'].mean():+.3f} % | {t_stat(x['move_pct']):.2f} |")
    p.to_csv(RES / "S3_B2_stageA_trades.csv", index=False)
    (RES / "S3_B2_stageA_report.md").write_text("\n".join(L_) + "\n", encoding="utf-8")
    print("\n".join(L_[:16]))
    return {"pass": ok, "n": len(p), "mean": m, "t": t}


if __name__ == "__main__":
    for s in sys.argv[1:] or ["B", "A"]:
        {"B": run_b, "A": run_a}[s]()
