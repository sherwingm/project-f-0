"""Excel writer for scanner.fade_indicators: Summary first, readable headers, widths, % / Rs formats, frozen headers, filters."""
from __future__ import annotations

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEAD = PatternFill("solid", fgColor="1F3864")
GOOD, BAD = PatternFill("solid", fgColor="E2EFDA"), PatternFill("solid", fgColor="FCE4D6")
F, FB, FH = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True), Font(name="Arial", size=10, bold=True, color="FFFFFF")


def fmt_for(col: str) -> str | None:
    c = col.lower()
    if c.startswith("p ("):
        return "0.000"
    if "rs" in c.split() or c.endswith("rs") or "net rs" in c:
        return '"₹"#,##0;[Red]-"₹"#,##0;-'
    if "%" in c or "rsi" in c or "gap_pct" in c:
        return '0.0;[Red]-0.0;-'
    if "trades" in c or "no entry" in c:
        return "0"
    return None


def sheet(wb: Workbook, title: str, df: pd.DataFrame, note: str, flag: str | None = None) -> None:
    ws = wb.create_sheet(title)
    ws["A1"] = note
    ws["A1"].font = Font(name="Arial", size=10, italic=True)
    ws["A1"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=min(12, max(1, len(df.columns))))
    ws.row_dimensions[1].height = 48
    for j, col in enumerate(df.columns, 1):
        c = ws.cell(row=2, column=j, value=col)
        c.font, c.fill = FH, HEAD
        c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 42
    fm = [fmt_for(str(c)) for c in df.columns]
    for i, row in enumerate(df.itertuples(index=False), 3):
        for j, v in enumerate(row, 1):
            if isinstance(v, float) and pd.isna(v):
                v = None
            if hasattr(v, "item"):
                v = v.item()
            c = ws.cell(row=i, column=j, value=v)
            c.font = F
            if fm[j - 1] and isinstance(v, (int, float)) and not isinstance(v, bool):
                c.number_format = fm[j - 1]
        if flag and flag in df.columns:
            r = df.iloc[i - 3]
            if r[flag] == "yes" and (r.get("p (fail vs rest)") or 1) < 0.05:
                fill = BAD if r.get("reads as") == "fails MORE" else GOOD
                for j in range(1, len(df.columns) + 1):
                    ws.cell(row=i, column=j).fill = fill
    for j, col in enumerate(df.columns, 1):
        w = max(len(str(col)) * 0.55, 9)
        if j == 1 or str(col) in ("condition", "entry rule", "symbol"):
            w = max(w, min(60, df[col].astype(str).str.len().max() * 1.0 + 2))
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "B3"
    ws.auto_filter.ref = f"A2:{get_column_letter(len(df.columns))}{len(df) + 2}"


def write(path, f, single, pairs, why, timing, timing_rows) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    sig = single[(single["same way both halves"] == "yes") & (single["p (fail vs rest)"] < 0.05)]
    sigp = pairs[(pairs["same way both halves"] == "yes") & (pairs["p (fail vs rest)"] < 0.05)]
    sigw = why[(why["same way both halves"] == "yes") & (why["p (fail vs rest)"] < 0.05)]
    base = timing.iloc[0]
    best = timing.iloc[1:].sort_values("mean net %", ascending=False).iloc[0]
    lines = [
        ("S1 v12 fade · RSI, EMA 50/100/200, Supertrend vs the fade's failures", FB),
        (f"{len(f)} backtest trades (Oct 2024 – Aug 2026), v12 exit, real charges. Fail = net < 0. Exploratory: many conditions are tested, "
         "so a row is marked only when p < 0.05 AND it points the same way in both halves (train before 3 Nov 2025, test after).", F),
        ("", F),
        ("Part A · known before the 09:16 buy (daily values at the previous close; gaps at 09:15)", FB),
        (f"Single conditions that pass: {len(sig)} of {len(single)}" + ("" if sig.empty else ": " + "; ".join(
            f"{r['condition']} ({r['reads as']}: {r['fail %']:.0f} % vs {r['fail % rest']:.0f} %)" for _, r in sig.iterrows())), F),
        (f"Pairs that pass: {len(sigp)} of {len(pairs)} (pairs with at least 20 trades)" + ("" if sigp.empty else ". Top: " + "; ".join(
            f"{r['condition']} ({r['fail %']:.0f} % vs {r['fail % rest']:.0f} %)" for _, r in sigp.head(5).iterrows())), F),
        (f"Inside the gap-down days ({int(why['trades'].max() if len(why) else 0)} trades max per row), conditions that pass: {len(sigw)}"
         + ("" if sigw.empty else ": " + "; ".join(f"{r['condition']} ({r['fail %']:.0f} % vs {r['fail % rest']:.0f} %)" for _, r in sigw.iterrows())), F),
        ("", F),
        ("Part B · entry time on the option's own 1-minute candles (wait from 09:30 to 13:00, buy at the next candle's open + 1 tick)", FB),
        (f"09:16 live rule: {int(base['trades taken'])} trades, fail {base['fail %']:.1f} %, mean {base['mean net %']:+.2f} % a trade, "
         f"total ₹{base['total Rs']:,.0f}.", F),
        (f"Best waiting rule by mean: {best['entry rule']}: {int(best['trades taken'])} trades, fail {best['fail %']:.1f} %, "
         f"mean {best['mean net %']:+.2f} % (the same trades bought at 09:16: {best['same trades at 09:16: mean net %']:+.2f} %); "
         f"train {best['train mean net %']:+.2f} %, test {best['test mean net %']:+.2f} %.", F),
        ("", F),
        ("Sheets: Single indicators · Pairs · Inside gap-down days · Entry timing · Entry timing per trade · Trades (every trade with "
         "its indicator values, for your own analysis: filter any column). Red rows fail more, green rows fail less (marked rows only).", F),
        ("Indicator settings: RSI 14 (Wilder), EMA 50/100/200 on closes, Supertrend 10 × 3 ATR. Daily values are from the previous "
         "close, so all of Part A is known before the open. Nifty daily from Yahoo Finance (^NSEI); stocks from data/eod2.", F),
    ]
    for i, (txt, font) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=txt)
        c.font = font
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 150
    sheet(wb, "Single indicators", single, "Each condition alone vs every other trade. Marked rows: p < 0.05 and the same way in both halves.",
          "same way both halves")
    sheet(wb, "Pairs", pairs, "Every pair of conditions (both true), at least 20 trades, sorted by p. With ~1,000 pairs, several "
          "will pass by chance: trust only rows that also make sense.", "same way both halves")
    sheet(wb, "Inside gap-down days", why.sort_values("p (fail vs rest)"), "Only Nifty gap-down days: which condition separates the "
          "failures from the rest on those days (the 'why').", "same way both halves")
    sheet(wb, "Entry timing", timing, "Waiting rules on the option's 1-minute candles vs the 09:16 entry. 'same trades at 09:16' "
          "compares on exactly the trades the rule took.")
    sheet(wb, "Entry timing per trade", timing_rows, "One row per trade: the 09:16 result and each waiting rule's entry time and net.")
    cols = ["day0", "half", "symbol", "side", "strike", "lot", "entry 09:16+tick", "v12 why", "v12 net %", "v12 net Rs", "max up %",
            "max dip %", "fail", "nifty_pct"] + [c for c in f.columns if c.startswith(("nifty_", "stock_")) and c != "nifty_pct"]
    sheet(wb, "Trades", f[cols].rename(columns={"nifty_pct": "nifty close move %"}), "Every trade with its indicator values "
          "(previous close) and the 09:15 gaps. Use the filters to test your own ideas.")
    wb.save(path)
