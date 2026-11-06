"""Expiry-day blasts workbook + report: data/results/expiry_blasts_2026-11-05.xlsx and expiry_blasts.md
(from scanner/expiry_blasts.py CSVs).

    python scripts/expiry_blasts_xlsx.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RES = Path(__file__).resolve().parents[1] / "data" / "results"
OUT = RES / "expiry_blasts_2026-11-05.xlsx"
FONT, BOLD = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True, color="FFFFFF")
HEAD = PatternFill("solid", fgColor="1F4E78")
HOT = PatternFill("solid", fgColor="E2EFDA")


def style(ws, widths, fmt: dict):
    for c in ws[1]:
        c.font, c.fill = BOLD, HEAD
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = FONT
            if c.column in fmt:
                c.number_format = fmt[c.column]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 42
    ws.auto_filter.ref = ws.dimensions


def prep():
    a = pd.read_csv(RES / "expiry_blasts_days.csv")
    a["best"] = a[["best_CE_x", "best_PE_x"]].max(axis=1)
    a["side"] = np.where(a["best_CE_x"] >= a["best_PE_x"], "Call", "Put")
    for c in ("strike", "paid", "peak_at", "1515_x"):
        a[f"b_{c}"] = np.where(a["side"] == "Call", a[f"best_CE_{c}"], a[f"best_PE_{c}"])
    a["one_way"] = np.maximum(a["up_from_0920_pct"], -a["down_from_0920_pct"])
    b = pd.read_csv(RES / "expiry_blasts_daily.csv")
    return a, b


def main() -> None:
    a, b = prep()
    wb = Workbook()
    s = wb.active
    s.title = "Summary"
    s.append(["Index", "Expiry days", "Best option ≥ 2x", "≥ 3x", "≥ 5x", "≥ 10x", "≥ 20x", "Median best multiple",
              "Share ≥ 2x", "Share ≥ 10x", "Call and put both ≥ 2x"])
    for u, g in a.groupby("index"):
        r = s.max_row + 1
        s.append([u, len(g)] + [int((g["best"] >= lv).sum()) for lv in (2, 3, 5, 10, 20)]
                 + [g["best"].median(), f"=C{r}/B{r}", f"=F{r}/B{r}",
                    int(((g["best_CE_x"] >= 2) & (g["best_PE_x"] >= 2)).sum())])
    style(s, [12, 10, 12, 8, 8, 8, 8, 12, 10, 10, 12], {8: "0.0\"x\"", 9: "0%", 10: "0%"})
    s.append([])
    s.append(["By the index's biggest one-way move after 09:20 (both indices)"])
    s.cell(s.max_row, 1).font = Font(name="Arial", size=10, bold=True)
    hdr = s.max_row + 1
    s.append(["One-way move", "Expiry days", "≥ 10x days", "Share ≥ 10x", "Median best multiple", "≥ 2x days",
              "Share ≥ 2x"])
    for c in s[hdr]:
        c.font, c.fill = BOLD, HEAD
    for lo, hi, lab in ((0, 0.25, "under 0.25 %"), (0.25, 0.5, "0.25-0.5 %"), (0.5, 1, "0.5-1 %"), (1, 1.5, "1-1.5 %"), (1.5, 2, "1.5-2 %"),
                        (2, 99, "2 % or more")):
        g = a[(a["one_way"] >= lo) & (a["one_way"] < hi)]
        r = s.max_row + 1
        s.append([lab, len(g), int((g["best"] >= 10).sum()), f"=IF(B{r}=0,0,C{r}/B{r})", g["best"].median(),
                  int((g["best"] >= 2).sum()), f"=IF(B{r}=0,0,F{r}/B{r})"])
        s.cell(r, 4).number_format, s.cell(r, 5).number_format, s.cell(r, 7).number_format = "0%", "0.0\"x\"", "0%"
        for c in s[r]:
            c.font = FONT
    tb = a[a["best"] >= 10]
    s.append([])
    o = pd.read_csv(RES / "expiry_blasts_options.csv")
    o["held"] = o["x_1515"] - 1
    o["cap2"] = np.where(o["x"] >= 2, 1.0, o["held"])
    notes = [
        "What it means",
        f"2x is common: the best option of the day doubled from 09:20 on {int((a[a['index']=='NIFTY']['best']>=2).sum())} of "
        f"{int((a['index']=='NIFTY').sum())} NIFTY and {int((a[a['index']=='SENSEX']['best']>=2).sum())} of "
        f"{int((a['index']=='SENSEX').sum())} SENSEX expiry days; every day the index moved ≥ 1 % one way had one.",
        "A single fixed option (one side, one strike, chosen at 09:20) doubles on 30-49 % of expiry days (NIFTY calls "
        "~30-36 %, NIFTY puts ~43-49 % near the money, SENSEX ~38-47 %), but is still ≥ 2x at 15:15 on only 5-23 %.",
        "Selling at 2x if touched, else at 15:15, averages −8 % to −58 % a trade for calls and +8 % (at the money) to "
        "−75 % (10 strikes out) for puts, before charges and slippage (sheet 2x by strike). Puts doing better is this "
        "two-year window, not a rule.",
        f"About 1 expiry day in 7 has an option that goes 10x from its 09:20 price (NIFTY {int((a[a['index']=='NIFTY']['best']>=10).sum())} "
        f"of {int((a['index']=='NIFTY').sum())}, SENSEX {int((a[a['index']=='SENSEX']['best']>=10).sum())} of "
        f"{int((a['index']=='SENSEX').sum())}, Oct 2024 → Oct 2026). With weekly NIFTY and SENSEX expiries that is ~2 a month.",
        "They need the index to travel 1 % or more one way after 09:20: under 0.5 % none of 80 days blasted, 0.5-1 % "
        "6 of 83, 1-1.5 % 11 of 36, 1.5 % or more 12 of 16.",
        f"Most give it back: of the {len(tb)} 10x days, the best option was still ≥ 10x at 15:15 on "
        f"{int((tb['b_1515_x'] >= 10).sum())} and below the 09:20 price on {int((tb['b_1515_x'] < 1).sum())}.",
        "The side and strike are known only afterwards: the best of 22 strikes is picked here in hindsight. Buying both "
        "sides every expiry day lost on average (data/results/S3_expiry_day_scan.md: call + put 4 strikes out −8 %, median −98 %).",
        "Today, 5 Nov 2026: SENSEX +2.6 % (+2,008 points) is a big index day (top ~4 % of expiry days here); the 79000 call "
        "₹12.75 → ₹309.95 is ~24x from the previous close. Today's SENSEX minutes arrive with the nightly data update.",
    ]
    for i, n in enumerate(notes):
        s.append([n])
        s.cell(s.max_row, 1).font = Font(name="Arial", size=10, bold=(i == 0))

    x2 = wb.create_sheet("2x by strike")
    x2.append(["Index", "Option", "Strikes out", "Days", "Median paid 09:20 (₹)", "Doubled (≥ 2x)", "Tripled (≥ 3x)",
               "Still ≥ 2x at 15:15", "Held to 15:15, mean", "Held to 15:15, median", "Sell at 2x else 15:15, mean"])
    for (u, opt, k), g in o.groupby(["index", "opt", "otm"]):
        x2.append([u, "Call" if opt == "CE" else "Put", int(k), len(g), g["paid"].median(), (g["x"] >= 2).mean(),
                   (g["x"] >= 3).mean(), (g["x_1515"] >= 2).mean(), g["held"].mean(), g["held"].median(),
                   g["cap2"].mean()])
    style(x2, [9, 7, 9, 7, 11, 10, 10, 11, 11, 11, 13],
          {5: "₹#,##0.00", 6: "0%", 7: "0%", 8: "0%", 9: "0%", 10: "0%", 11: "0%"})

    how = wb.create_sheet("How it's calculated")
    for x, y in [
        ("How it's calculated", ""),
        ("1-minute part", "NIFTY and SENSEX weekly expiry days in the index store, Oct 2024 → Oct 2026. On each expiry day: "
                          "calls and puts 0-10 strikes out of the money from the 09:20 spot (NIFTY 50-point, SENSEX 100-point "
                          "steps), only options priced ≥ ₹2 at 09:20. Multiple = highest minute high after 09:20 ÷ the 09:20 "
                          "price. 'Best' = the largest multiple of the day across those strikes (hindsight)."),
        ("2x by strike", "Every option 0-10 strikes out, both sides, one row per index / side / distance: how often it "
                         "doubled after 09:20, how often it was still ≥ 2x at 15:15, and a 'sell at 2x if touched, else "
                         "15:15' result (before charges and slippage). File expiry_blasts_options.csv."),
        ("At 15:15", "The same best option's 15:15 price ÷ its 09:20 price: what was left if not sold at the peak."),
        ("Index move", "Close vs the previous close; one-way = the larger of the rise or fall from the 09:20 spot."),
        ("Daily part", "NSE daily bhavcopy, NIFTY and BANKNIFTY, every expiry day 2018 → 2026: per option the day's high ÷ "
                       "its open (open ≥ ₹2, traded), and the close ÷ the previous close (what a broker app shows as 1D %). "
                       "BANKNIFTY weekly expiries stopped in Nov 2024 (monthly only since); NIFTY weeklies began Feb 2019."),
        ("Not included", "Slippage and charges; this counts what the market did, not a trade."),
        ("Files", "scanner/expiry_blasts.py; data/results/expiry_blasts_days.csv, expiry_blasts_daily.csv."),
    ]:
        how.append([x, y])
    how["A1"].font = Font(name="Arial", size=12, bold=True)
    for r in range(2, how.max_row + 1):
        how.cell(r, 1).font = Font(name="Arial", size=10, bold=True)
        how.cell(r, 2).font = FONT
        how.cell(r, 2).alignment = Alignment(wrap_text=True, vertical="top")
    how.column_dimensions["A"].width = 16
    how.column_dimensions["B"].width = 110

    d = wb.create_sheet("Expiry days (1-min)")
    d.append(["Index", "Expiry day", "Weekday", "Index close vs prev %", "Rise from 09:20 %", "Fall from 09:20 %",
              "Best multiple", "Side", "Strike", "Paid 09:20 (₹)", "Peak at", "At 15:15 (x of paid)",
              "Options ≥ 5x", "Options ≥ 10x"])
    for r in a.sort_values("expiry_day", ascending=False).itertuples():
        d.append([r.index, r.expiry_day, r.weekday, r.move_close_pct / 100, r.up_from_0920_pct / 100,
                  r.down_from_0920_pct / 100, r.best, r.side, r.b_strike, r.b_paid, r.b_peak_at,
                  None if pd.isna(r.b_1515_x) else r.b_1515_x, int(r.CE_5x + r.PE_5x), int(r.CE_10x + r.PE_10x)])
        if r.best >= 10:
            for c in d[d.max_row]:
                c.fill = HOT
    style(d, [9, 11, 8, 11, 10, 10, 10, 6, 9, 10, 8, 11, 9, 9],
          {4: "0.00%", 5: "0.00%", 6: "0.00%", 7: "0.0\"x\"", 9: "#,##0", 10: "₹#,##0.00", 12: "0.00\"x\""})

    y = wb.create_sheet("By year (daily, 2018-)")
    y.append(["Index", "Year", "Expiry days", "Best high/open ≥ 5x", "≥ 10x", "≥ 20x", "Close/prev close ≥ 10x",
              "Close/prev close ≥ 20x"])
    for (u, yr), g in b.groupby(["index", "year"]):
        y.append([u, str(yr), len(g), int((g["best_hi_open_x"] >= 5).sum()), int((g["best_hi_open_x"] >= 10).sum()),
                  int((g["best_hi_open_x"] >= 20).sum()), int((g["best_close_prev_x"] >= 10).sum()),
                  int((g["best_close_prev_x"] >= 20).sum())])
    for u in ("BANKNIFTY", "NIFTY"):
        rows = [r for r in range(2, y.max_row + 1) if y.cell(r, 1).value == u]
        r0, r1 = rows[0], rows[-1]
        y.append([u, "Total"] + [f"=SUM({get_column_letter(c)}{r0}:{get_column_letter(c)}{r1})" for c in range(3, 9)])
        for c in y[y.max_row]:
            c.font = Font(name="Arial", size=10, bold=True)
    style(y, [11, 8, 10, 12, 9, 9, 13, 13], {})
    for r in range(2, y.max_row + 1):
        for c in y[r]:
            c.font = Font(name="Arial", size=10, bold=y.cell(r, 2).value == "Total")
    wb._sheets.sort(key=lambda w: ["Summary", "2x by strike", "How it's calculated"].index(w.title)
                    if w.title in ("Summary", "2x by strike", "How it's calculated") else 3)
    wb.save(OUT)

    md = ["# Expiry-day option blasts (2026-11-05, descriptive)", "",
          "The user's screenshot: SENSEX 05 Nov 79000 call ₹12.75 → ₹309.95 (+2,331 %) on expiry day, SENSEX +2.6 %. "
          "\"check how many have these happens previous\". Code `scanner/expiry_blasts.py`, workbook "
          "`expiry_blasts_2026-11-05.xlsx`.", ""]
    md += [f"- {n}" for n in notes[1:]]
    (RES / "expiry_blasts.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
