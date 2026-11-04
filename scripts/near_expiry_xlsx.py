"""Near-expiry max-up workbook: data/results/near_expiry_maxup_2026-11-04.xlsx (from scanner/near_expiry_maxup.py CSVs).

    python scripts/near_expiry_xlsx.py

Sheets: Summary (headline per days to expiry), How it's calculated, NIFTY by strike (formulas over the NIFTY trades
sheet), Stocks by strike (values: 1M+ rows do not fit a formula sheet; source CSV named), NIFTY trades.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.formula import ArrayFormula

RES = Path(__file__).resolve().parents[1] / "data" / "results"
OUT = RES / "near_expiry_maxup_2026-11-04.xlsx"
FONT, BOLD = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True, color="FFFFFF")
HEAD = PatternFill("solid", fgColor="1F4E78")
PCT, RS = "0%;-0%;0%", "₹#,##0.00"
OPT = {"CE": "Call", "PE": "Put"}


def style(ws, widths, pct_cols=(), rs_cols=()):
    for c in ws[1]:
        c.font, c.fill = BOLD, HEAD
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = FONT
            if c.column in pct_cols:
                c.number_format = PCT
            elif c.column in rs_cols:
                c.number_format = RS
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 45
    ws.auto_filter.ref = ws.dimensions


def prep():
    a = pd.read_csv(RES / "near_expiry_nifty_trades.csv")
    b = pd.read_csv(RES / "near_expiry_stocks_trades.csv", dtype={"excluded": str})
    b = b[b["excluded"].isna()]                     # splits, bonuses, demergers, changed contracts: left out
    a["slip"] = np.where(a["otm"] < 2, 0.005, 0.01)
    tgt = (2 * (1 - a["slip"]) - 1) * 100
    a["cap_day"] = np.where(a["max_up_day"] >= 100, tgt, a["sold_day"])
    a["cap_held"] = np.where(a["max_up"] >= 100, tgt, a["held"])
    b["cap_held"] = np.where(b["max_close_up"] >= 100, (2 * (1 - 0.005) - 1) * 100, b["held"])
    return a, b


def headline(a, b) -> pd.DataFrame:
    rows = []
    for name, df, up, extra in (("NIFTY", a, "max_up", True), ("Stocks", b, "max_close_up", False)):
        for (opt, k), g in df.groupby(["opt", "k"]):
            u = g[up].dropna()
            rows.append({
                "Underlying": name, "Option": OPT[opt], "Sessions to expiry": int(k), "Trades": len(g),
                "Median paid (₹)": g["entry"].median(), "Max up mean": u.mean() / 100, "Max up median": u.median() / 100,
                "Reached +100 %": (u >= 100).mean(), "Reached +200 %": (u >= 200).mean(),
                "Reached +500 %": (u >= 500).mean(),
                "Sold same day 15:15, mean": g["sold_day"].mean() / 100 if extra else None,
                "Held to expiry, mean": g["held"].mean() / 100, "Held to expiry, median": g["held"].median() / 100,
                "Sell at +100 % else hold, mean": g["cap_held"].mean() / 100,
                "Sell at +100 % else 15:15 same day, mean": g["cap_day"].mean() / 100 if extra else None,
            })
    return pd.DataFrame(rows)


def main() -> None:
    a, b = prep()
    wb = Workbook()
    s = wb.active
    s.title = "Summary"
    h = headline(a, b)
    s.append(list(h.columns))
    for r in h.itertuples(index=False):
        s.append([None if (isinstance(v, float) and np.isnan(v)) else v for v in r])
    style(s, [10, 7, 10, 8, 10, 10, 10, 10, 10, 10, 12, 11, 11, 13, 15], pct_cols=range(6, 16), rs_cols=(5,))

    how = wb.create_sheet("How it's calculated")
    lines = [
        ("How it's calculated", ""),
        ("Question", "Near-expiry option buying (the user, 2026-11-04): how often does an option bought by a fixed rule "
                     "reach +100 %, and what does holding it pay, by sessions to expiry (0 = expiry day)."),
        ("NIFTY", "1-minute option prices, every weekly expiry Oct 2024 → Oct 2026 (107 expiries), sessions 0-4 before "
                  "it. Buy at 09:20: the 09:20 close + 0.5 % slippage (1 % for 2+ strikes out). ATM = 09:20 spot "
                  "rounded to 50; calls and puts 0-6 strikes (50 points each) out of the money."),
        ("Stocks", "NSE daily bhavcopy closes, every monthly stock expiry Jan 2021 → Aug 2026, every F&O stock, "
                   "sessions 1-10 before expiry. Buy at the day's close + 0.5 % (only contracts that traded that day, "
                   "close ≥ ₹0.05). ATM = strike nearest the underlying (before Jul 2024: the stock future's close)."),
        ("Max up", "NIFTY: highest minute high after entry up to expiry 15:29, % over the price paid. Stocks: highest "
                   "CLOSE on a later traded day up to expiry: a lower bound, intraday highs are not in the data."),
        ("Held to expiry", "NIFTY: expiry-day 15:15 close − slippage. Stocks: intrinsic value at the expiry-day "
                           "underlying close (no STT or delivery cost; stock options are physically settled)."),
        ("Sell at +100 % else hold", "A resting sell at 2× the price paid; if the price ever touches it, the trade "
                                     "books +100 % (less slippage), else it is held to expiry as above."),
        ("Left out", "Stock rows hit by a split, bonus, demerger or other corporate action between entry and expiry, or whose contract NSE re-struck (3,130 of 1,468,785; column excluded in the CSV). A few ₹0.05 prints remain (e.g. MCX Oct 2023, MOTHERSUMI Jan 2022): they make the stock MEANS jumpy; read medians and win rates first."),
        ("Not included", "Charges (≈ ₹40-60 a lot round trip, large against a ₹2-10 option); Kotak's extra delivery "
                         "margin on stock options in the last 4 sessions."),
        ("Read with care", "Descriptive only, in-sample, no rule chosen. Max up is hindsight: nobody sells at the "
                           "exact top. Percent columns are averages of per-trade %, one contract each, not ₹ P&L."),
        ("Files", "Trades: data/results/near_expiry_nifty_trades.csv, near_expiry_stocks_trades.csv. Code: "
                  "scanner/near_expiry_maxup.py, scripts/near_expiry_xlsx.py."),
    ]
    for x, y in lines:
        how.append([x, y])
    how["A1"].font = Font(name="Arial", size=12, bold=True)
    for r in range(2, len(lines) + 1):
        how.cell(r, 1).font = Font(name="Arial", size=10, bold=True)
        how.cell(r, 2).font = FONT
        how.cell(r, 2).alignment = Alignment(wrap_text=True, vertical="top")
    how.column_dimensions["A"].width = 24
    how.column_dimensions["B"].width = 100

    # NIFTY trades (raw) + formula summary by strike
    t = wb.create_sheet("NIFTY trades")
    t.append(["Expiry", "Entry day", "Sessions to expiry", "Option", "Strikes out", "Strike", "Spot 09:20",
              "Paid (₹)", "Max up to expiry", "Max up same day", "Peak day", "Peak at", "Sold 15:15 same day",
              "Held to expiry", "Sell at +100 % else hold"])
    for r in a.sort_values(["day", "opt", "otm"]).itertuples():
        t.append([r.expiry, r.day, r.k, OPT[r.opt], r.otm, r.strike, r.spot, r.entry, r.max_up / 100,
                  r.max_up_day / 100, r.peak_day, r.peak_at,
                  None if pd.isna(r.sold_day) else r.sold_day / 100, None if pd.isna(r.held) else r.held / 100,
                  None if pd.isna(r.cap_held) else r.cap_held / 100])
    style(t, [11, 11, 9, 7, 8, 8, 10, 9, 10, 10, 11, 7, 10, 10, 11], pct_cols=(9, 10, 13, 14, 15), rs_cols=(8,))
    n = t.max_row
    rng = {c: f"'NIFTY trades'!${c}$2:${c}${n}" for c in "CDEIMNO"}

    ns = wb.create_sheet("NIFTY by strike")
    ns.append(["Option", "Sessions to expiry", "Strikes out", "Trades", "Max up median", "Reached +100 %",
               "Sold 15:15 same day, mean", "Held to expiry, mean", "Sell at +100 % else hold, mean"])
    row = 2
    for opt in ("Call", "Put"):
        for k in range(5):
            for o in range(7):
                c = f'{rng["D"]},$A{row},{rng["C"]},$B{row},{rng["E"]},$C{row}'
                ns.append([opt, k, o, f"=COUNTIFS({c})",
                           ArrayFormula(f"E{row}", f'=MEDIAN(IF(({rng["D"]}=$A{row})*({rng["C"]}=$B{row})*({rng["E"]}=$C{row}),{rng["I"]}))'),
                           f'=COUNTIFS({c},{rng["I"]},">=1")/D{row}',
                           f'=AVERAGEIFS({rng["M"]},{c})', f'=AVERAGEIFS({rng["N"]},{c})',
                           f'=AVERAGEIFS({rng["O"]},{c})'])
                row += 1
    style(ns, [8, 10, 9, 8, 10, 10, 12, 12, 13], pct_cols=range(5, 10))

    st = wb.create_sheet("Stocks by strike")
    st.append(["Option", "Sessions to expiry", "Strikes out", "Trades", "Median paid (₹)", "Max close up median",
               "Reached +100 % (close)", "Held to expiry, mean", "Held to expiry, won", "Sell at +100 % else hold, mean"])
    for (opt, k, o), g in b.groupby(["opt", "k", "otm"]):
        u = g["max_close_up"].dropna()
        st.append([OPT[opt], int(k), int(o), len(g), g["entry"].median(), u.median() / 100, (u >= 100).mean(),
                   g["held"].mean() / 100, (g["held"] > 0).mean(), g["cap_held"].mean() / 100])
    style(st, [8, 10, 9, 8, 10, 11, 11, 11, 10, 13], pct_cols=range(6, 11), rs_cols=(5,))

    wb._sheets.sort(key=lambda w: ["Summary", "How it's calculated", "NIFTY by strike", "Stocks by strike",
                                   "NIFTY trades"].index(w.title))
    wb.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
