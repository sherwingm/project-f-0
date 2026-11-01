"""Max up workbook for the five buy tests: data/results/S3_maxup_2026-11-01.xlsx (from S3_F4_maxup_trades.csv).

    python scripts/s3_maxup_xlsx.py

Sheets: How it's calculated, Summary (formulas over the trade sheets), one sheet per test.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RES = Path(__file__).resolve().parents[1] / "data" / "results"
OUT = RES / "S3_maxup_2026-11-01.xlsx"
NAMES = {"E1": "Event straddle", "Q1": "Squeeze", "B1": "Breakout + volume", "G1": "Gap follow-through",
         "P4": "Old P4 breakout"}
HOLD = {"E1": "Overnight: 14:45 the day before → 14:45 event day", "Q1": "3 sessions: 14:45 → 14:45",
        "B1": "Intraday: breakout +1 min → stop / trail / 15:15", "G1": "Intraday: 09:30 → stop / trail / 15:15",
        "P4": "Intraday: breakout +1 min → stop / trail / 15:15"}
FONT, BOLD = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True, color="FFFFFF")
HEAD = PatternFill("solid", fgColor="1F4E78")
PCT = "0.0%;-0.0%;0.0%"


def style(ws, widths):
    for c in ws[1]:
        c.font, c.fill = BOLD, HEAD
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = FONT
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 32


def main() -> None:
    m = pd.read_csv(RES / "S3_F4_maxup_trades.csv")
    wb = Workbook()
    how = wb.active
    how.title = "How it's calculated"
    lines = [
        ("How it's calculated", ""),
        ("Window", "2024-10-01 → 2026-10-28 (P4: 2024-10-01 → 2025-09-30), NIFTY 1-minute option prices."),
        ("Trade result (Net % of premium)", "(sell price − buy price) × quantity − all charges, ÷ premium paid. Buy fills include 0.5 % slippage "
         "(1 % before 09:30, after 15:00 or 2+ strikes out); charges from server/charges.py."),
        ("Avg per trade", "The simple average of Net % of premium over all trades of the test."),
        ("Max up while held", "Highest value of the bought option(s) from the minute after entry to the exit minute, "
         "as % above the price paid (before exit costs)."),
        ("Max up any time", "Same, but up to 15:29 of the exit day: what was there if the exit had been different."),
        ("Prices used", "Each minute's last traded price, carried forward; a minute where any leg had no trade for 30 min "
         "is skipped."),
        ("Intraday?", "Breakout + volume, Gap follow-through and P4: yes, in and out the same day. Event straddle: overnight "
                      "(day before → event day). Squeeze: held 3 sessions."),
        ("Note", "Max up is descriptive: picking an exit from it would be fitting on data already seen."),
    ]
    for a, b in lines:
        how.append([a, b])
    how["A1"].font = Font(name="Arial", size=12, bold=True)
    for r in range(2, len(lines) + 1):
        how.cell(r, 1).font = Font(name="Arial", size=10, bold=True)
        how.cell(r, 2).font = FONT
        how.cell(r, 2).alignment = Alignment(wrap_text=True, vertical="top")
    how.column_dimensions["A"].width = 26
    how.column_dimensions["B"].width = 95

    summ = wb.create_sheet("Summary", 0)
    summ.append(["Test", "How long held", "Trades", "Avg booked net", "Median booked net", "Median max up held",
                 "Median max up any time", "Reached +20 % held", "Reached +50 % held", "Reached +100 % held",
                 "Reached +50 % any time"])
    for i, pod in enumerate(NAMES, start=2):
        g = m[m["pod"] == pod]
        ws = wb.create_sheet(NAMES[pod])
        ws.append(["Day", "Entry", "Exit day", "Exit time", "Exit reason", "Option(s) bought: strike@buy>sell",
                   "Booked net % of premium", "Max up while held", "Peak while held at", "Max up any time",
                   "Peak any time at"])
        for r in g.sort_values("day").itertuples():
            ws.append([r.day, r.entry, r.exit_day, r.exit_at, r.reason, r.legs, r.net_pct_premium / 100,
                       r.max_up_held_pct / 100, r.peak_held_at, r.max_up_any_pct / 100, r.peak_any_at])
        for row in ws.iter_rows(min_row=2):
            for k in (6, 7, 9):
                row[k].number_format = PCT
        style(ws, [11, 7, 11, 8, 9, 34, 12, 12, 17, 12, 17])
        ws.auto_filter.ref = ws.dimensions
        n, q = ws.max_row, f"'{NAMES[pod]}'"
        G, H, J = (f"{q}!{c}2:{c}{n}" for c in "GHJ")
        summ.append([NAMES[pod], HOLD[pod], f"=COUNT({G})", f"=AVERAGE({G})", f"=MEDIAN({G})", f"=MEDIAN({H})",
                     f"=MEDIAN({J})", f'=COUNTIF({H},">=0.2")', f'=COUNTIF({H},">=0.5")', f'=COUNTIF({H},">=1")',
                     f'=COUNTIF({J},">=0.5")'])
        for k in (3, 4, 5, 6):
            summ.cell(i, k + 1).number_format = PCT
    style(summ, [18, 40, 8, 11, 11, 12, 12, 10, 10, 10, 11])
    wb._sheets.sort(key=lambda s: {"Summary": 0, "How it's calculated": 1}.get(s.title, 2))
    wb.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
