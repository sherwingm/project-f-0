"""Rupee result of simple expiry-day buying rules on the blast data (the user, 2026-11-06: "Check how much profit we
are taking from it in options"). Adds sheet "Profit (₹)" to data/results/expiry_blasts_2026-11-05.xlsx and writes
data/results/expiry_blasts_pnl.csv.

    python scripts/expiry_blasts_pnl.py          (after scanner.expiry_blasts and scripts/expiry_blasts_xlsx.py)

Every NIFTY / SENSEX expiry day with prices (Oct 2024 → Oct 2026): ₹10,000 into one option at 09:20 (+0.5 % slippage,
1 % for 2+ strikes out), sold − the same slippage, charges from server/charges.py on both legs. Rules: hold to 15:15;
sell at 2x / 3x / 5x of the price paid if the minute high touches it, else 15:15; and the hindsight ceiling (sold at
the day's exact top, impossible in practice).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import charges as C  # noqa: E402

RES = Path(__file__).resolve().parents[1] / "data" / "results"
STAKE = 10_000
RULES = {"hold": "Hold to 15:15", "t2": "Sell at 2x else 15:15", "t3": "Sell at 3x else 15:15",
         "t5": "Sell at 5x else 15:15", "peak": "Sold at the day's top (hindsight, impossible)"}


def build() -> pd.DataFrame:
    o = pd.read_csv(RES / "expiry_blasts_options.csv").dropna(subset=["x_1515"]).reset_index(drop=True)
    slip = np.where(o["otm"] < 2, 0.005, 0.01)
    o["buy"] = o["paid"] * (1 + slip)
    qty = STAKE / o["buy"]

    def pnl(exit_px):
        ex = np.maximum(exit_px, 0)
        ch = [C.leg("CE", "BUY", q, b)["total"] + C.leg("CE", "SELL", q, e)["total"] for q, b, e in zip(qty, o["buy"], ex)]
        return (ex - o["buy"]) * qty - np.array(ch)

    o["hold"] = pnl(o["paid"] * o["x_1515"] * (1 - slip))
    for t in (2, 3, 5):
        o[f"t{t}"] = pnl(np.where(o["x"] >= t, o["buy"] * t * (1 - slip), o["paid"] * o["x_1515"] * (1 - slip)))
    o["peak"] = pnl(o["paid"] * o["x"] * (1 - slip))
    return o


def main() -> None:
    o = build()
    o.to_csv(RES / "expiry_blasts_pnl.csv", index=False)
    wb = load_workbook(RES / "expiry_blasts_2026-11-05.xlsx")
    if "Profit (₹)" in wb.sheetnames:
        del wb["Profit (₹)"]
    ws = wb.create_sheet("Profit (₹)", 1)
    head = ["Index", "Option", "Strikes out", "Trades"] + [f"{v}, total ₹" for v in RULES.values()] + \
           ["Sell at 2x: avg ₹ a trade", "Sell at 2x: won"]
    ws.append(head)
    for (u, opt, k), g in o.groupby(["index", "opt", "otm"]):
        ws.append([u, "Call" if opt == "CE" else "Put", int(k), len(g)] + [round(g[c].sum()) for c in RULES]
                  + [round(g["t2"].mean()), (g["t2"] > 0).mean()])
    for (u, k), g in o.groupby(["index", "otm"]):
        ws.append([u, "Call + put", int(k), len(g)] + [round(g[c].sum()) for c in RULES]
                  + [round(g["t2"].mean()), (g["t2"] > 0).mean()])
    bold = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    for c in ws[1]:
        c.font, c.fill = bold, PatternFill("solid", fgColor="1F4E78")
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = Font(name="Arial", size=10)
            if 5 <= c.column <= 10:
                c.number_format = "₹#,##0;[Red]-₹#,##0"
            if c.column == 11:
                c.number_format = "0%"
    for i, w in enumerate([9, 11, 9, 7, 13, 13, 13, 13, 16, 13, 9], start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    ws.freeze_panes, ws.row_dimensions[1].height = "A2", 45
    ws.auto_filter.ref = ws.dimensions
    r = ws.max_row + 2
    ws.cell(r, 1, f"₹{STAKE:,} into one option at 09:20 on every expiry day, Oct 2024 → Oct 2026; slippage and charges "
                  "included. 'Call + put' buys both (₹20,000 a day). The last rule is the ceiling nobody can reach.")
    ws.cell(r, 1).font = Font(name="Arial", size=10, italic=True)
    wb.save(RES / "expiry_blasts_2026-11-05.xlsx")
    print("ok", len(o))


if __name__ == "__main__":
    main()
