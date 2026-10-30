"""S3 L1 (strategies/S3_L1_vix_rising_long_straddle.md): NIFTY long ATM straddle when India VIX > 22 and rising,
held 5 sessions, on the daily NSE bhavcopy 2018-01 → 2021-12. Also `count`: the qualifying days 2018-01 → 2025-09.

    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_l1 count   # step 2: signal days only, no prices
    INDEX_STORE=<index-data checkout>/data/index python -m scanner.s3_l1 run     # -> data/results/S3_L1_report.md
"""
from __future__ import annotations

import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

from index_data import load as L
from index_data.index_close import load as index_close
from scanner.s3_p1 import gate, max_drawdown, monte_carlo, summary
from scanner.s3_pods import RES, page_commit
from server import charges

PAGE = "strategies/S3_L1_vix_rising_long_straddle.md"
WINDOW = (date(2018, 1, 1), date(2021, 12, 31))
HALVES = ((date(2018, 1, 1), date(2019, 12, 31)), (date(2020, 1, 1), date(2021, 12, 31)))
COUNT_END = date(2025, 9, 30)
VIX, LOOKBACK, HOLD, MIN_DTE, MIN_VOL, SLIP = 22.0, 5, 5, 10, 100, 0.01
LOT_CHANGE = date(2021, 7, 29)        # NSE circular 28/2021: lot 75 -> 50 for contracts expiring from here
OUT, CSV = RES / "S3_L1_report.md", RES / "S3_L1_trades.csv"


def lot_for(expiry: date) -> int:
    return 50 if expiry >= LOT_CHANGE else 75


def bhav(lo: date, hi: date) -> pd.DataFrame:
    parts = []
    for p in sorted((L._store() / "options_daily" / "NIFTY").glob("*.parquet")):
        if lo.strftime("%Y-%m") <= p.stem <= hi.strftime("%Y-%m"):
            parts.append(L.read_store(p, columns=["TradDt", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric",
                                                     "TtlTradgVol"]))
    b = pd.concat(parts)
    b = b[b["FinInstrmTp"] == "IDO"].copy()
    b["TradDt"], b["XpryDt"] = pd.to_datetime(b["TradDt"]).dt.date, pd.to_datetime(b["XpryDt"]).dt.date
    return b[(b["TradDt"] >= lo) & (b["TradDt"] <= hi)]


def vix_series() -> tuple[pd.Series, pd.Series]:
    """(NSE official India VIX close, NSE official NIFTY 50 close), by date."""
    c = index_close()
    v = c[c["index"] == "INDIAVIX"].set_index("date")["close"].sort_index()
    n = c[c["index"] == "NIFTY50"].set_index("date")["close"].sort_index()
    return v, n


def signals(sessions: list[date], vix: pd.Series, thr: float = VIX) -> dict[date, tuple[float, float]]:
    """{d: (vix_d, vix_d-5)} for sessions where VIX(d) > thr and VIX(d) > VIX(d - 5 sessions). Closes only."""
    out = {}
    for i, d in enumerate(sessions):
        if i < LOOKBACK or d not in vix.index or sessions[i - LOOKBACK] not in vix.index:
            continue
        a, b = float(vix[d]), float(vix[sessions[i - LOOKBACK]])
        if a > thr and a > b:
            out[d] = (a, b)
    return out


def count() -> None:
    v, _ = vix_series()
    sessions = [d for d in v.index if date(2017, 12, 1) <= d <= COUNT_END]
    sig = {d: x for d, x in signals(sessions, v).items() if d >= date(2018, 1, 1)}
    by_year = pd.Series([d.year for d in sig]).value_counts().sort_index()
    print(f"sessions 2018-01-01 → {COUNT_END}: {sum(d >= date(2018, 1, 1) for d in sessions)}")
    print(f"qualifying days (NSE official VIX): {len(sig)}  by year: {by_year.to_dict()}")
    yv = L.read_store(L._store() / "vix_daily.parquet").dropna(subset=["close"])
    yv = yv.set_index(pd.to_datetime(yv["date"]).dt.date)["close"]
    ys = {d: x for d, x in signals([d for d in sessions if d in yv.index], yv).items() if d >= date(2018, 1, 1)}
    print(f"qualifying days (vix_daily, yfinance): {len(ys)}; only official: {sorted(set(sig) - set(ys))}; "
          f"only yfinance: {sorted(set(ys) - set(sig))}")
    both = [d for d in sessions if d in yv.index and d >= date(2018, 1, 1)]
    diff = (v.reindex(both) - yv.reindex(both)).abs()
    print(f"VIX official vs yfinance on {len(both)} common days: max |diff| {diff.max():.3f}, >0.05 on {(diff > 0.05).sum()} days")
    print(f"sessions without official VIX: {[d for d in sessions if d not in v.index][:5]}")


def leg_px(b_idx, day, expiry, k, opt) -> tuple[float | None, int]:
    r = b_idx.get((day, expiry, k, opt))
    return (None, 0) if r is None else (float(r[0]), int(r[1]))


def exit_price(b_idx, sessions, xi, expiry, k, opt) -> tuple[float | None, date | None]:
    """ClsPric on the exit session if the leg traded; else the next session it traded, at most 2 later, before expiry."""
    for j in range(xi, min(xi + 3, len(sessions))):
        d = sessions[j]
        if d >= expiry:
            break
        px, vol = leg_px(b_idx, d, expiry, k, opt)
        if px and vol > 0:
            return px, d
    return None, None


def simulate(b: pd.DataFrame, sessions: list[date], sig_days: set[date], vix: pd.Series, spot: pd.Series,
             hold: int = HOLD, cost_mult: float = 1.0, window=WINDOW) -> tuple[pd.DataFrame, list[dict]]:
    b_idx = {(r.TradDt, r.XpryDt, r.StrkPric, r.OptnTp): (r.ClsPric, r.TtlTradgVol) for r in b.itertuples()}
    by_day = {d: g for d, g in b.groupby("TradDt")}
    pos = {d: i for i, d in enumerate(sessions)}
    rows, skipped, busy_until = [], [], None
    slip = SLIP * cost_mult
    for d in sorted(sig_days):
        if busy_until is not None and d < busy_until:
            continue
        i = pos[d]
        if i + 1 >= len(sessions):
            continue
        e_day = sessions[i + 1]
        g = by_day.get(e_day)
        exps = sorted(x for x in g["XpryDt"].unique() if x >= e_day + timedelta(days=MIN_DTE)) if g is not None else []
        if not exps:
            skipped.append({"signal": d, "entry": e_day, "why": "no expiry ≥ 10 days out"})
            continue
        ex = exps[0]
        c = g[(g["XpryDt"] == ex) & (g["TtlTradgVol"] >= MIN_VOL) & (g["ClsPric"] > 0)]
        piv = c.pivot_table(index="StrkPric", columns="OptnTp", values="ClsPric", aggfunc="first").dropna()
        if piv.empty or not {"CE", "PE"} <= set(piv.columns):
            skipped.append({"signal": d, "entry": e_day, "why": f"no strike with both legs ≥ {MIN_VOL} contracts"})
            continue
        k = float((piv["CE"] - piv["PE"]).abs().idxmin())
        ce0, pe0 = float(piv.loc[k, "CE"]), float(piv.loc[k, "PE"])
        ei = i + 1
        xi = ei + hold
        if xi >= len(sessions):
            continue
        reason = f"{hold} sessions"
        before = [j for j in range(ei + 1, xi + 1) if sessions[j] < ex]
        if not before:
            skipped.append({"signal": d, "entry": e_day, "why": "expiry before the first exit session"})
            continue
        if before[-1] < xi:
            xi, reason = before[-1], "last session before expiry"
        if sessions[xi] > window[1]:
            skipped.append({"signal": d, "entry": e_day, "why": "planned exit after the window"})
            continue
        ce1, dce = exit_price(b_idx, sessions, xi, ex, k, "CE")
        pe1, dpe = exit_price(b_idx, sessions, xi, ex, k, "PE")
        busy_until = max(x for x in (dce, dpe, sessions[xi]) if x)
        if ce1 is None or pe1 is None:
            skipped.append({"signal": d, "entry": e_day, "why": "data gap at exit", "strike": k, "expiry": ex,
                            "ce_last": leg_px(b_idx, sessions[xi], ex, k, "CE")[0],
                            "pe_last": leg_px(b_idx, sessions[xi], ex, k, "PE")[0]})
            continue
        lot = lot_for(ex)
        bce, bpe, sce, spe = ce0 * (1 + slip), pe0 * (1 + slip), ce1 * (1 - slip), pe1 * (1 - slip)
        fees = cost_mult * (charges.leg("CE", "BUY", lot, bce)["total"] + charges.leg("PE", "BUY", lot, bpe)["total"]
                            + charges.leg("CE", "SELL", lot, sce)["total"] + charges.leg("PE", "SELL", lot, spe)["total"])
        debit = (bce + bpe) * lot
        net = (sce + spe) * lot - debit - fees
        rows.append({"signal_day": d, "day": e_day, "exit_day": max(dce, dpe), "expiry": ex, "monthly_only": e_day < date(2019, 2, 11),
                     "vix": float(vix.get(d, np.nan)), "strike": k, "spot_close": float(spot.get(e_day, np.nan)),
                     "ce_in": ce0, "pe_in": pe0, "ce_out": ce1, "pe_out": pe1, "exit_fallback": (dce != sessions[xi]) or (dpe != sessions[xi]),
                     "lot": lot, "debit_rs": round(debit, 2), "fees_rs": round(fees, 2), "net_rs": round(net, 2),
                     "net_pct_premium": net / debit * 100, "reason": reason})
    return pd.DataFrame(rows), skipped


def run() -> None:
    commit = page_commit(PAGE)
    b = bhav(date(2017, 12, 1), WINDOW[1] + timedelta(days=20))
    vix, spot = vix_series()
    sessions = sorted(b["TradDt"].unique())
    in_win = lambda s: {d for d in s if WINDOW[0] <= d <= WINDOW[1]}
    sig = in_win(signals(sessions, vix))
    prim, skipped = simulate(b, sessions, sig, vix, spot)
    prim2, _ = simulate(b, sessions, sig, vix, spot, cost_mult=2.0)
    neigh = {"VIX > 17.6": simulate(b, sessions, in_win(signals(sessions, vix, VIX * 0.8)), vix, spot)[0],
             "VIX > 26.4": simulate(b, sessions, in_win(signals(sessions, vix, VIX * 1.2)), vix, spot)[0],
             "hold 4": simulate(b, sessions, sig, vix, spot, hold=4)[0],
             "hold 6": simulate(b, sessions, sig, vix, spot, hold=6)[0]}
    base, _ = simulate(b, sessions, in_win(set(sessions)), vix, spot)
    g = gate(prim, prim2, list(neigh.values()), HALVES)
    write(commit, sig, prim, prim2, neigh, base, skipped, g)


def _row(name: str, t: pd.DataFrame) -> str:
    s = summary(t)
    if not s.get("n"):
        return f"| {name} | 0 | | | | | | | |"
    return (f"| {name} | {s['n']} | {s['win'] * 100:.0f} % | {s['mean_pct']:+.1f} % | {s['median_pct']:+.1f} % | "
            f"{s['t_pct']:.2f} | {s['mean_rs']:+,.0f} | {s['total_rs']:+,.0f} | {s['worst_rs']:+,.0f} |")


def write(commit, sig, prim, prim2, neigh, base, skipped, g) -> None:
    s = summary(prim)
    mc = monte_carlo(prim["net_rs"]) if len(prim) else (0, 0, 0)
    lines = [f"# S3 L1 · NIFTY long straddle when VIX > 22 and rising: 2018-01 → 2021-12", "",
             f"Page `{PAGE}` at commit `{commit}`. Script `scanner/s3_l1.py`. Daily NSE bhavcopy closes; signal from NSE's "
             "official India VIX close. 1 lot; slippage 1 % a fill; `server/charges.py` at today's rates.", "",
             f"**Verdict: {'PASS' if g['pass'] else 'FAIL'}**", "",
             "| Check | Result |", "|---|---|"] + [f"| {k} | {'✔' if v else '✘'} |" for k, v in g["checks"].items()]
    if "halves" in g:
        lines.append(f"| halves (mean % of debit) | {g['halves'][0]:+.1f} % · {g['halves'][1]:+.1f} % |")
    lines += ["", f"Signal days in the window: {len(sig)}. Traded: {len(prim)}. Skipped: {len(skipped)}.", "",
              "| Cell | Trades | Won | Mean % of debit | Median | t | Mean ₹ | Total ₹ | Worst ₹ |",
              "|---|---|---|---|---|---|---|---|---|", _row("**L1 primary**", prim), _row("L1 at 2× costs", prim2)]
    lines += [_row(f"neighbour: {k}", v) for k, v in neigh.items()]
    lines += [_row("baseline: every session, no VIX filter", base), ""]
    if s.get("n"):
        lines += [f"Max drawdown (₹, 1 lot, date order): {s['max_dd_rs']:+,.0f}. Monte Carlo drawdown 5 / 50 / 95 %: "
                  f"{mc[0]:+,.0f} / {mc[1]:+,.0f} / {mc[2]:+,.0f}. Average month (months with trades): {s['avg_month_rs']:+,.0f}. "
                  f"Fees + slippage paid on average: ₹{prim['fees_rs'].mean():,.0f} fees a trade.", "",
                  "By year (mean % of debit · trades): " + " · ".join(
                      f"{y}: {gr['net_pct_premium'].mean():+.1f} % ({len(gr)})" for y, gr in prim.groupby(pd.to_datetime(prim["day"]).dt.year)),
                  "", f"Exit fallback used (a leg had no trade on the exit session): {int(prim['exit_fallback'].sum())} trades. "
                  f"Monthly-only expiries (before weekly NIFTY options): {int(prim['monthly_only'].sum())} trades. "
                  f"ATM strike minus official close at entry: median {(prim['strike'] - prim['spot_close']).median():+.0f}, "
                  f"max |·| {(prim['strike'] - prim['spot_close']).abs().max():.0f}.", ""]
        lines += ["## Trades", "", "| Signal | Entry | Exit | Expiry | VIX | Strike | CE in → out | PE in → out | Lot | Net ₹ | Net % |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in prim.itertuples():
            lines.append(f"| {r.signal_day} | {r.day} | {r.exit_day} | {r.expiry} | {r.vix:.1f} | {r.strike:.0f} | "
                         f"{r.ce_in:.1f} → {r.ce_out:.1f} | {r.pe_in:.1f} → {r.pe_out:.1f} | {r.lot} | {r.net_rs:+,.0f} | {r.net_pct_premium:+.1f} % |")
    if skipped:
        lines += ["", "## Skipped signals", ""] + [f"- {x['signal']} (entry {x['entry']}): {x['why']}" +
                                                   (f"; {x['strike']:.0f} exp {x['expiry']}, last CE {x['ce_last']}, PE {x['pe_last']}" if x.get("strike") else "")
                                                   for x in skipped]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    prim.to_csv(CSV, index=False)
    print(f"wrote {OUT}: {'PASS' if g['pass'] else 'FAIL'} {g['checks']}")


if __name__ == "__main__":
    {"count": count, "run": run}[sys.argv[1] if len(sys.argv) > 1 else "count"]()
