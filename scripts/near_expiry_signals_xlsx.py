"""Near-expiry signal screen workbook + report: data/results/near_expiry_signals_2026-11-04.xlsx and near_expiry_signals.md.

    python scripts/near_expiry_signals_xlsx.py        (after python -m scanner.near_expiry_signals)

Sheets: Summary, How it's calculated, Feature screen (test window, 108 cells), Top-day check, G1 by days to expiry.
Values are computed here from the CSVs named on "How it's calculated" (date-clustered t cannot be a sheet formula).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scanner.stats import clustered_t  # noqa: E402

RES = Path(__file__).resolve().parents[1] / "data" / "results"
OUT = RES / "near_expiry_signals_2026-11-04.xlsx"
FONT, BOLD = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True, color="FFFFFF")
HEAD = PatternFill("solid", fgColor="1F4E78")
GOOD, BAD = PatternFill("solid", fgColor="E2EFDA"), PatternFill("solid", fgColor="FCE4D6")
FEAT = {"gap_al": "Opening gap, in the option's direction %", "first5_al": "09:15 → 09:20 move, in direction %",
        "prev_al": "Previous day's return, in direction %", "ret5_al": "Previous 5-day return, in direction %",
        "ema_al": "09:20 spot vs 20-day EMA, in direction %", "vix": "India VIX at 09:20",
        "vix_chg": "VIX change since previous close (points)", "prev_range": "Previous day's range % of close",
        "iv_rv": "ATM straddle vs recent moves (< 1 = cheap)"}
OPT = {"CE": "Call", "PE": "Put"}


def style(ws, widths, pct=(), num=()):
    for c in ws[1]:
        c.font, c.fill = BOLD, HEAD
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = FONT
            if c.column in pct:
                c.number_format = "0%;-0%;0%"
            elif c.column in num:
                c.number_format = "0.0"
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = w
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 40
    ws.auto_filter.ref = ws.dimensions


def top_days(a: pd.DataFrame) -> pd.DataFrame:
    s = pd.read_csv(RES / "near_expiry_signals_screen.csv")
    rows = []
    for r in s[(s["held_net_mean"] > 0) | (s["day_net_mean"] > 0)].itertuples():
        cuts = r.range
        g = a[(a["opt"] == r.opt)]
        lo, hi = -np.inf, np.inf
        if cuts.startswith("≤"):
            hi = float(cuts[2:])
        elif cuts.startswith(">"):
            lo = float(cuts[2:])
        else:
            lo, hi = (float(x) for x in cuts.split(" – "))
        g = g[(g[r.feature] > lo) & (g[r.feature] <= hi)]
        for ex in ("held_net", "day_net"):
            if getattr(r, f"{ex}_mean") <= 0:
                continue
            d = g.groupby("day")[ex].sum().sort_values(ascending=False)
            rows.append({"Feature": FEAT[r.feature], "Bin": r.bin, "Range": r.range, "Option": OPT[r.opt],
                         "Exit": "Held to expiry" if ex == "held_net" else "Sold 15:15 same day",
                         "Trades": len(g), "Mean net": g[ex].mean() / 100, "Top 3 days": ", ".join(d.index[:3]),
                         "Mean without top 3 days": g[~g["day"].isin(d.index[:3])][ex].mean() / 100})
    return pd.DataFrame(rows)


def g1_split() -> pd.DataFrame:
    d = pd.read_csv(RES / "S3_G1_datasheet.csv")
    d["Near expiry"] = np.where(d["Days to expiry"] <= 3, "1-3 days", "4-5 days")
    d["Half"] = np.where(d["Day"] < "2025-10-01", "Oct 2024 – Sep 2025", "Oct 2025 – Oct 2026")
    rows = []
    for keys, g in list(d.groupby(["Near expiry", "Half"])) + list(d.groupby(["Near expiry"])):
        keys = keys if isinstance(keys, tuple) and len(keys) == 2 else (keys[0] if isinstance(keys, tuple) else keys, "Both")
        x = g["G1 net %"]
        top = g.nlargest(3, "G1 net %").index
        rows.append({"Days to expiry": keys[0], "Period": keys[1], "Trades": len(g), "Mean net": x.mean() / 100,
                     "Median net": x.median() / 100, "t (date-clustered)": clustered_t(x, g["Day"]),
                     "Won": (x > 0).mean(), "Max up ≥ +100 %": (g["G1 max up held %"] >= 100).mean(),
                     "Mean without top 3 trades": g.drop(top)["G1 net %"].mean() / 100, "Net ₹ (1 lot)": g["G1 net ₹"].sum()})
    return pd.DataFrame(rows)


def main() -> None:
    a = pd.read_csv(RES / "near_expiry_signals_trades.csv")
    s = pd.read_csv(RES / "near_expiry_signals_screen.csv")
    td, g1 = top_days(a), g1_split()
    wb = Workbook()
    summ = wb.active
    summ.title = "Summary"
    base = a.groupby("opt").agg(n=("entry", "size"), days=("day", "nunique"), hit=("hit100", "mean"),
                                dn=("day_net", "mean"), hn=("held_net", "mean"))
    best = s.loc[s["held_net_t"].idxmax()]
    worst = s.nsmallest(3, "held_net_t")
    lines = [
        ("Near-expiry signal screen (test window Oct 2024 – Sep 2025, NIFTY, 09:20 buys 0-4 sessions to expiry)", ""),
        ("Baseline, calls", f"{int(base.loc['CE','n'])} trades on {int(base.loc['CE','days'])} days; +100 % reached "
                            f"{base.loc['CE','hit']:.0%}; net {base.loc['CE','dn']:+.1f} % sold same day, "
                            f"{base.loc['CE','hn']:+.1f} % held to expiry"),
        ("Baseline, puts", f"{int(base.loc['PE','n'])} trades; +100 % reached {base.loc['PE','hit']:.0%}; net "
                           f"{base.loc['PE','dn']:+.1f} % same day, {base.loc['PE','hn']:+.1f} % held"),
        ("Answer", "No 09:20 feature picks the +100 % trades. 108 cells: no positive cell reaches t 2 (best "
                   f"{FEAT[best.feature]}, {best.bin}, {OPT[best.opt]}: {best.held_net_mean:+.1f} % held, t "
                   f"{best.held_net_t:.2f}). Each positive cell is carried by its 3 best days (for calls, nearly always the "
                   "16-17 Apr and 15 May 2025 rallies): without them 24 of 25 turn negative; the one left (puts, spot "
                   "within 0.9 % of the 20-day EMA, held) is +5 % (sheet Top-day check)."),
        ("What to avoid (strong)", "; ".join(f"{OPT[r.opt]}s with {FEAT[r.feature]} {r.bin} ({r.range}): "
                                             f"{r.held_net_mean:+.0f} % held, t {r.held_net_t:.1f}" for r in worst.itertuples())),
        ("The one lead", "G1 (downside opening-range breakout put, already pre-registered, forward test from "
                         "2026-11-05) earns its money near expiry: trades 1-3 days out +5.6 % (2024-25) and +19.2 % "
                         "(2025-26) a trade; 4-5 days out +9.4 % then -4.6 %. Not significant (t 0.6 / 1.7) and found "
                         "after the fact (G1's own sample)."),
        ("Holdout", "Not used. No candidate passed the S3 test gate (t ≥ 2), so nothing opens it."),
        ("Read with care", "In-sample screen; ~5 of 108 cells reach |t| ≥ 2 by chance. Net of charges, 1 lot."),
    ]
    for x, y in lines:
        summ.append([x, y])
    summ["A1"].font = Font(name="Arial", size=12, bold=True)
    for r in range(2, len(lines) + 1):
        summ.cell(r, 1).font = Font(name="Arial", size=10, bold=True)
        summ.cell(r, 2).font = FONT
        summ.cell(r, 2).alignment = Alignment(wrap_text=True, vertical="top")
    summ.column_dimensions["A"].width = 22
    summ.column_dimensions["B"].width = 110

    how = wb.create_sheet("How it's calculated")
    for x, y in [
        ("How it's calculated", ""),
        ("Trades", "data/results/near_expiry_nifty_trades.csv: NIFTY, 09:20 buy (close + 0.5 % slippage, 1 % for 2+ strikes "
                   "out), weekly expiries, 0-4 sessions to expiry, calls / puts 0-6 strikes out. Only entry days "
                   "2024-10-01 → 2025-09-30 (the S3 test window); the holdout is not read."),
        ("Net %", "(exit − entry) × lot − charges (server/charges.py: ₹20 an order, STT 0.15 % on the sell, exchange, "
                  "SEBI, stamp, GST), ÷ premium paid. Same day = 15:15 close − slippage; held = expiry-day 15:15."),
        ("Features", "Known at 09:20, fixed before the screen ran (scanner/near_expiry_signals.py). 'In direction' = "
                     "positive when NIFTY moved the option's way (up for calls, down for puts)."),
        ("Bins", "Terciles of each feature over the test window's trade-days, same cut for calls and puts."),
        ("t", "Mean ÷ date-clustered standard error (all strikes bought on one day count as one cluster)."),
        ("Top-day check", "For each positive cell: the 3 days with the largest summed net, and the cell's mean "
                          "without them."),
        ("G1 split", "From data/results/S3_G1_datasheet.csv (259 G1 trades, Oct 2024 – Oct 2026, in-sample)."),
    ]:
        how.append([x, y])
    how["A1"].font = Font(name="Arial", size=12, bold=True)
    for r in range(2, how.max_row + 1):
        how.cell(r, 1).font = Font(name="Arial", size=10, bold=True)
        how.cell(r, 2).font = FONT
        how.cell(r, 2).alignment = Alignment(wrap_text=True, vertical="top")
    how.column_dimensions["A"].width = 18
    how.column_dimensions["B"].width = 110

    sc = wb.create_sheet("Feature screen")
    sc.append(["Feature", "Bin", "Range", "Option", "Trades", "Days", "Reached +100 %", "Sold same day, mean net",
               "t", "Held to expiry, mean net", "t "])
    for r in s.itertuples():
        sc.append([FEAT[r.feature], r.bin, r.range, OPT[r.opt], r.trades, r.days, r.hit100 / 100, r.day_net_mean / 100,
                   r.day_net_t, r.held_net_mean / 100, r.held_net_t])
        for col in (9, 11):
            t = sc.cell(sc.max_row, col).value
            if t is not None and t <= -2:
                sc.cell(sc.max_row, col).fill = BAD
            elif t is not None and t >= 2:
                sc.cell(sc.max_row, col).fill = GOOD
    style(sc, [40, 7, 14, 7, 8, 7, 10, 12, 7, 12, 7], pct=(7, 8, 10), num=(9, 11))

    tt = wb.create_sheet("Top-day check")
    tt.append(list(td.columns))
    for r in td.itertuples(index=False):
        tt.append(list(r))
    style(tt, [40, 7, 14, 7, 18, 8, 10, 36, 14], pct=(7, 9))

    gg = wb.create_sheet("G1 by days to expiry")
    gg.append(list(g1.columns))
    for r in g1.itertuples(index=False):
        gg.append(list(r))
    style(gg, [12, 20, 8, 10, 10, 10, 8, 11, 14, 14], pct=(4, 5, 7, 8, 9), num=(6,))
    for row in gg.iter_rows(min_row=2):
        row[9].number_format = "₹#,##0;-₹#,##0"
    wb.save(OUT)

    md = ["# Near-expiry signal screen (2026-11-04, test window only, descriptive)", "",
          "The user: \"find the signal\" that picks the +100 % near-expiry trades. Code `scanner/near_expiry_signals.py`; "
          "workbook `near_expiry_signals_2026-11-04.xlsx`. NIFTY 09:20 buys 0-4 sessions to expiry, entry days "
          "2024-10-01 → 2025-09-30; net of charges, 1 lot; holdout not read.", ""]
    md += [f"- **{x}.** {y}" for x, y in lines[1:]]
    md += ["", "## G1 by days to expiry (in-sample, G1's own trades)", "",
           "| Days to expiry | Period | Trades | Mean net | t | Won | Mean without top 3 |", "|---|---|---|---|---|---|---|"]
    for r in g1.itertuples(index=False):
        md.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]:+.1%} | {r[5]:.2f} | {r[6]:.0%} | {r[8]:+.1%} |")
    (RES / "near_expiry_signals.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
