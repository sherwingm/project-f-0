"""Trade-level audit workbook (offline): 30 S1 fade trades and 20 G1 trades, each with the candles the decision used.

    python -m stress_audit.trade_audit            (run after s1_stress and g1_stress)

Selection (PREREG.md section 8, deterministic, seed 20261113): 3 largest wins, 3 largest losses, 4 stops, 4 trail (S1) / next-close (G1) exits,
3 ambiguous-candle trades, 3 gap-through stops, 3 largest friction, then a seeded random fill. A trade is listed once, under the first reason it met.
Observed = a traded price in the file. Assumed = tick / slippage / the delay this audit adds. Nothing is changed in any production file.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("INDEX_STORE", str(Path(__file__).resolve().parents[2] / "fo-index-data" / "data" / "index"))   # before index_data is imported

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from index_data import load as L
from server import charges as ch

from . import common as C
from . import g1_stress as G
from . import s1_stress as S

COMPONENTS = ("brokerage", "stt", "exchange", "sebi", "stamp", "gst")


def pick(df: pd.DataFrame, plan: list[tuple[str, str, str, int]], total: int, seed=C.SEED) -> pd.DataFrame:
    """plan rows: (label, mask column, order: 'desc'|'asc'|'random', how many) -> first meeting trades, one listing each."""
    rng = np.random.default_rng(seed)
    chosen, why = [], {}
    for label, col, order, k in plan:
        pool = df[df[col]] if col != "all" else df
        pool = pool[~pool["tid"].isin(chosen)]
        if order == "random":
            ids = list(pool["tid"].to_numpy())
            rng.shuffle(ids)
            take = ids[:k]
        else:
            key = {"wins": ("net_rs", False), "losses": ("net_rs", True), "friction": ("friction", False), "gap": ("gap_depth", False)}.get(label.split(" ")[0], ("net_rs", False))
            take = list(pool.sort_values(key[0], ascending=key[1])["tid"].head(k))
        for t in take:
            chosen.append(t)
            why[t] = label
    rest = df[~df["tid"].isin(chosen)]
    ids = list(rest["tid"].to_numpy())
    rng.shuffle(ids)
    for t in ids[: max(0, total - len(chosen))]:
        chosen.append(t)
        why[t] = "seeded random fill"
    out = df[df["tid"].isin(chosen)].copy()
    out["why_selected"] = out["tid"].map(why)
    return out.sort_values("signal_day")


def charges_parts(side, lot, px, leg, on=None) -> dict:
    kw = {"on": on} if on is not None else {}
    r = ch.leg(side, leg, lot, px, **kw)
    return {f"{leg.lower()}_{c}": r[c] for c in COMPONENTS} | {f"{leg.lower()}_total": r["total"]}


def s1_part(trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = S.run_scenario(trades, "B0")
    H = S.run_scenario(trades, "S0H", order="H")[["tid", "net_rs", "reason"]].rename(columns={"net_rs": "net_rs_orderH", "reason": "reason_orderH"})
    d = base.merge(H, on="tid").merge(trades[["tid", "set", "tick", "entry_B"]], on="tid")
    rows, candles = [], []
    for r in d.itertuples():
        t = trades.loc[r.tid]
        c = t.candles
        e = r.entry
        stop, trig = e * 0.8, e * 1.1
        idx = int(r.exit_idx)
        seen = c.iloc[1: idx + 1]
        amb = bool(((seen["l"] <= stop) & (seen["h"] >= trig)).any())
        gap = bool(r.reason == "stop" and c.iloc[idx]["o"] < stop)
        peak = float(c.iloc[1: idx]["h"].max()) if idx > 1 and r.reason == "trail" else None
        lvl = peak * 0.98 if peak else None
        fr = r.charges_rs + 2 * t.tick * t.lot
        row = {"tid": r.tid, "signal_day": r.day0, "stock": r.symbol, "side": r.side, "strike": t.strike, "contract_set": t.set, "lot": t.lot,
               "0916_candle_open_OBSERVED": float(c.iloc[0]["o"]), "0916_high_OBSERVED": float(c.iloc[0]["h"]), "0916_low_OBSERVED": float(c.iloc[0]["l"]),
               "entry_fill_ASSUMED_(open+tick)": e, "stop_level_(0.80 x entry)": round(stop, 4), "trail_trigger_(1.10 x entry)": round(trig, 4),
               "exit_candle": r.exit_candle, "exit_reason": r.reason, "minutes_held": r.minutes_held,
               "exit_candle_open_OBSERVED": float(c.iloc[idx]["o"]), "exit_candle_low_OBSERVED": float(c.iloc[idx]["l"]),
               "peak_before_exit_OBSERVED": peak, "trail_level_(0.98 x peak)": round(lvl, 4) if lvl else None,
               "exit_fill_ASSUMED_(level or open, minus tick)": r.exit, **charges_parts(r.side, r.lot, e, "BUY"), **charges_parts(r.side, r.lot, r.exit, "SELL"),
               "charges_rs": r.charges_rs, "net_rs": r.net_rs, "net_pct": r.net_pct, "ambiguous_candle_(stop and +10 % in one candle)": amb,
               "gap_through_stop": gap, "net_rs_if_high_before_low_ordering": r.net_rs_orderH, "exit_if_high_before_low": r.reason_orderH,
               "friction": fr, "gap_depth": (stop - float(c.iloc[idx]["o"])) if gap else 0.0, "live_record": "none for this date (the live ledger starts 15 Oct 2026; history ends Aug 2026)"}
        rows.append(row)
        for j in range(0, min(len(c), idx + 2)):
            q = c.iloc[j]
            candles.append({"tid": r.tid, "stock": r.symbol, "signal_day": r.day0, "candle": q["t"], "open": q["o"], "high": q["h"], "low": q["l"], "close": q["c"],
                            "volume": q["volume"], "role": "entry candle" if j == 0 else ("EXIT candle" if j == idx else "")})
    t = pd.DataFrame(rows)
    t["amb"] = t["ambiguous_candle_(stop and +10 % in one candle)"]
    t["gapm"] = t["gap_through_stop"]
    t["is_stop"] = t["exit_reason"] == "stop"
    t["is_trail"] = t["exit_reason"] == "trail"
    t["wins"] = t["net_rs"] > 0
    t["losses"] = t["net_rs"] <= 0
    plan = [("wins (largest)", "wins", "desc", 3), ("losses (largest)", "losses", "asc", 3), ("ambiguous candle", "amb", "random", 3),
            ("gap-through stop (deepest gap)", "gapm", "desc", 3), ("friction (largest charges + tick vs premium)", "all", "desc", 3),
            ("stop exit", "is_stop", "random", 4), ("trail exit", "is_trail", "random", 4)]
    sel = pick(t, plan, 30)
    return sel, pd.DataFrame(candles)


def g1_part() -> tuple[pd.DataFrame, pd.DataFrame]:
    trades = G.collect()
    trades["day0"] = trades["day"].astype(str)
    rp = pd.read_csv(C.ROOT / "g1_research" / "results" / "g1_live_replay_trades.csv")
    trades["g1f"] = trades["day0"].map(dict(zip(rp["day"].astype(str), rp["g1f"] == 1))).fillna(False)
    base = G.run(trades.assign(half="x"), "B0")
    low = G.run(trades.assign(half="x"), "S5", stop_mode="low")[["tid", "net_rs", "reason"]].rename(columns={"net_rs": "net_rs_stop_on_minute_low", "reason": "reason_stop_on_minute_low"})
    d = base.merge(low, on="tid")
    rows, mins = [], []
    for r in d.itertuples():
        t = trades.loc[r.tid]
        k = r.strike
        df = t.chain[t.chain["strike"] == k]
        t_in = L.at(t.day, t.ent_h, t.ent_m)
        px0 = L.price_at(df, k, "PE", t_in, stale=3)
        fill_in = r.entry
        stop = fill_in * 0.5
        gap = bool(r.reason == "stop" and r.exit < 0.9 * stop)
        amb = bool(r.net_rs != r.net_rs_stop_on_minute_low and r.reason_stop_on_minute_low == "stop" and r.reason != "stop")
        fr = r.charges_rs + (fill_in - px0) * t.lot + 0.0
        exit_day = pd.Timestamp(r.exit_at).date()
        row = {"tid": r.tid, "signal_day": r.day0, "signal_minute": f"{t.ent_h:02d}:{t.ent_m:02d} minus 1 (entry is the next minute)", "entry_minute": r.entry_minute,
               "expiry": str(t.expiry), "NIFTY_spot_at_entry_OBSERVED": t.spot, "strike_(ATM_put)": k, "lot": t.lot, "g1f_track": bool(r.g1f),
               "entry_minute_close_OBSERVED": px0, "entry_fill_ASSUMED_(close_+_slippage)": fill_in, "stop_level_(0.50 x fill)": round(stop, 4),
               "exit_time": r.exit_at, "exit_reason": r.reason, "hours_held": r.hours_held, "exit_fill_ASSUMED_(mark_-_slippage)": r.exit,
               **charges_parts("PE", t.lot, fill_in, "BUY", on=t.day), **charges_parts("PE", t.lot, r.exit, "SELL", on=exit_day),
               "charges_rs": r.charges_rs, "net_rs": r.net_rs, "net_pct": r.net_pct, "ambiguous_(minute_low_touched_stop_but_close_did_not)": amb,
               "gap_through_stop_(sold_below_90pct_of_stop_level)": gap, "net_rs_if_stop_on_minute_low": r.net_rs_stop_on_minute_low,
               "friction": fr, "gap_depth": (stop - r.exit) if gap else 0.0, "live_record": "G1 live ledger (first trade 9 Nov 2026) is not on this PC; none matched"}
        rows.append(row)
        for lab, tt in (("entry", t_in), ("exit", pd.Timestamp(r.exit_at, tz=t_in.tz))):
            w = df[(df["timestamp"] >= tt - pd.Timedelta(minutes=3)) & (df["timestamp"] <= tt + pd.Timedelta(minutes=2))]
            for q in w.itertuples():
                mins.append({"tid": r.tid, "signal_day": r.day0, "around": lab, "minute": f"{q.timestamp:%Y-%m-%d %H:%M}", "open": q.open, "high": q.high, "low": q.low,
                             "close": q.close, "volume": q.volume})
    t = pd.DataFrame(rows)
    t["amb"] = t["ambiguous_(minute_low_touched_stop_but_close_did_not)"]
    t["gapm"] = t["gap_through_stop_(sold_below_90pct_of_stop_level)"]
    t["is_stop"] = t["exit_reason"] == "stop"
    t["is_time"] = t["exit_reason"] == "time"
    t["wins"] = t["net_rs"] > 0
    t["losses"] = t["net_rs"] <= 0
    plan = [("wins (largest)", "wins", "desc", 3), ("losses (largest)", "losses", "asc", 3), ("ambiguous minute", "amb", "random", 3),
            ("gap-through stop (deepest gap)", "gapm", "desc", 3), ("friction (largest charges + slippage vs premium)", "all", "desc", 3),
            ("stop exit", "is_stop", "random", 4), ("next-close exit", "is_time", "random", 4)]
    return pick(t, plan, 20), pd.DataFrame(mins)


def style(ws, money=(), pct=(), price=()):
    head = PatternFill("solid", fgColor="1F4E78")
    for c in ws[1]:
        c.font, c.fill, c.alignment = Font(bold=True, color="FFFFFF"), head, Alignment(wrap_text=True, vertical="center")
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = ws.dimensions
    names = [c.value for c in ws[1]]
    for i, name in enumerate(names, 1):
        col = get_column_letter(i)
        ws.column_dimensions[col].width = min(48, max(11, len(str(name)) * 0.55 + 4))
        fmt = "#,##0;[Red]-#,##0" if name in money else ("0.0" if name in pct else ("0.00" if name in price else None))
        if fmt:
            for cell in ws[col][1:]:
                cell.number_format = fmt
    ws.row_dimensions[1].height = 62


def write_df(wb, name, df, **kw):
    ws = wb.create_sheet(name)
    ws.append(list(df.columns))
    for row in df.itertuples(index=False):
        ws.append([None if (isinstance(v, float) and np.isnan(v)) else (bool(v) if isinstance(v, (np.bool_,)) else (v.item() if hasattr(v, "item") else v)) for v in row])
    style(ws, **kw)


def main() -> None:
    s1_trades = S.load_trades()
    s1_trades["tid"] = s1_trades.index
    s1_sel, s1_c = s1_part(s1_trades)
    g1_sel, g1_m = g1_part()
    drop = ["amb", "gapm", "is_stop", "is_trail", "is_time", "wins", "losses"]
    s1_sel = s1_sel.drop(columns=[c for c in drop if c in s1_sel.columns])
    g1_sel = g1_sel.drop(columns=[c for c in drop if c in g1_sel.columns])
    sc = pd.concat([pd.read_csv(C.OUT / "scenario_results_s1.csv"), pd.read_csv(C.OUT / "scenario_results_g1.csv")], ignore_index=True)
    cols = ["strategy", "scenario", "description", "price_type", "n", "net_rs", "exp_pct", "win_pct", "profit_factor", "max_dd_rs", "t_clustered",
            "ci95_cluster_lo", "ci95_cluster_hi", "delta_vs_B0_rs", "verdict"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    notes = [
        ("Trade-level audit - S1 fade v12 (30 trades) and G1 (20 trades)", ""),
        ("Built by", "stress_audit/trade_audit.py at the run recorded in RUN_MANIFEST.json (git commit, seed 20261113). Offline, existing files only."),
        ("How the trades were chosen", "Deterministic: 3 largest wins, 3 largest losses, 3 ambiguous-candle trades, 3 deepest gap-through stops, 3 largest friction, 4 stops, 4 trail (S1) / next-close (G1) exits, then a seeded random fill. A trade is listed once, under the first reason it met."),
        ("OBSERVED vs ASSUMED", "Columns marked OBSERVED are traded prices in the candle files. Columns marked ASSUMED are prices this audit or the engine chose (tick, slippage, delay, a level used as a fill). A candle high or low is a stress BOUND, never a guaranteed fill."),
        ("Charges", "Brokerage, STT, exchange, SEBI, stamp and GST for the buy and the sell leg, from server/charges.py. S1 uses the single 2026 table on every date (as the S1 backtest does); G1 uses the STT dated by trade day (as the S3 engine does). Rs 35.53 per lakh exchange charge on every date; the Rs 35.03 alternative is a separate scenario."),
        ("Live record", "No live trade overlaps these historical dates (S1 history ends Aug 2026, live from 15 Oct; G1 history ends 28 Oct, live from 9 Nov). Differences between history and live execution are listed in STRESS_REPORT.md."),
        ("Sheets", "S1 trades / S1 candles (every candle from entry to one candle after the exit) / G1 trades / G1 minutes (minutes around entry and exit) / Scenarios (every scenario, all strategies)."),
        ("Not proof", "Fifty trades illustrate how the engine books fills; they do not prove the strategy works. The verdicts are in STRESS_REPORT.md."),
    ]
    for a, b in notes:
        ws.append([a, b])
    ws["A1"].font = Font(bold=True, size=14)
    for r in range(2, ws.max_row + 1):
        ws.cell(r, 1).font = Font(bold=True)
        ws.cell(r, 2).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 120
    money = {c for c in list(s1_sel.columns) + list(g1_sel.columns) if "net_rs" in c or c.endswith("_total") or c == "charges_rs"}
    write_df(wb, "S1 trades", s1_sel.drop(columns=["friction", "gap_depth"]), money=money, pct={"net_pct"}, price={c for c in s1_sel.columns if "OBSERVED" in c or "ASSUMED" in c or "level" in c or "trigger" in c})
    write_df(wb, "S1 candles", s1_c[s1_c["tid"].isin(s1_sel["tid"])], price={"open", "high", "low", "close"})
    write_df(wb, "G1 trades", g1_sel.drop(columns=["friction", "gap_depth"]), money=money, pct={"net_pct"}, price={c for c in g1_sel.columns if "OBSERVED" in c or "ASSUMED" in c or "level" in c})
    write_df(wb, "G1 minutes", g1_m[g1_m["tid"].isin(g1_sel["tid"])], price={"open", "high", "low", "close"})
    write_df(wb, "Scenarios", sc[[c for c in cols if c in sc.columns]], money={"net_rs", "delta_vs_B0_rs", "max_dd_rs"}, pct={"exp_pct", "win_pct"})
    out = C.OUT / "TRADE_AUDIT.xlsx"
    wb.save(out)
    print("saved", out, len(s1_sel), "S1 trades,", len(g1_sel), "G1 trades")
    print(s1_sel["why_selected"].value_counts().to_dict())
    print(g1_sel["why_selected"].value_counts().to_dict())


if __name__ == "__main__":
    main()
