"""S1 fade · peak capture and entry quality on the 339 backtest trades (exploratory; strategies/S1_fade_entry_quality_audit.md).

    python -m scanner.fade_entry_quality

Peaks here are an OHLC PROXY (1-minute candle highs / closes), not bids: the history has no bid or ask. Writes
data/results/S1_fade_entry_quality_audit.md, _trades.csv and .xlsx. Nothing live changes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from server import charges as ch

from .build import ROOT
from .fade_stop_trail import SPLIT
from .stats import clustered_t

RES = ROOT / "data" / "results"
SETS = ("bandv10", "band12", "band12q4", "band050", "band050q4")
KEY = ["symbol", "day0", "side", "strike"]


def minutes() -> dict:
    by = {}
    for s in SETS:
        m = pd.read_csv(RES / f"S1_v10_{s}_minutes.csv")
        m["t"] = m["ts"].str[11:16]
        for k, g in m.groupby(KEY):
            if k not in by:
                g = g.sort_values("ts")
                by[k] = g[(g["t"] >= "09:16") & (g["t"] <= "15:19")].reset_index(drop=True)
    return by


def net_at(side: str, qty: int, e: float, px: float) -> float:
    return (px - e) * qty - ch.leg(side, "BUY", qty, e)["total"] - ch.leg(side, "SELL", qty, px)["total"]


def build() -> pd.DataFrame:
    by = minutes()
    t = pd.read_csv(RES / "S1_v12_exit_trades.csv")
    f = pd.read_csv(RES / "S1_v10_fade_diag_features.csv").drop_duplicates(["symbol", "day0", "side"])
    c = pd.read_csv(RES / "S1_fade_cheap_dte_trades.csv")[KEY + ["sessions_to_expiry"]].drop_duplicates(KEY)
    t = t.merge(f[["symbol", "day0", "side", "np_yoy", "np_qoq", "rev_yoy", "gap", "pre5", "pre20", "s_open",
                   "stock_fade_pct"]], on=["symbol", "day0", "side"], how="left").merge(c, on=KEY, how="left")
    rows = []
    for _, d in t.iterrows():
        r = d
        cd = by[(r.symbol, r.day0, r.side, float(r.strike))]
        e, q, sell, at = float(d["entry 09:16+tick"]), int(r.lot), float(d["v12 sell"]), d["v12 at"]
        held = cd[(cd["t"] >= "09:17") & (cd["t"] <= at)]
        hi_i = held["h"].idxmax()
        pk_hi, pk_cl, lo = float(held["h"].max()), float(held["c"].max()), float(held["l"].min())
        pn = net_at(r.side, q, e, pk_hi)
        net = float(d["v12 net Rs"])
        early = {}
        for n in (1, 3, 5):
            w = cd[cd["t"] >= "09:17"].head(n)
            early[f"first {n} min max up %"] = round((w["h"].max() / e - 1) * 100, 1)
            early[f"first {n} min max dip %"] = round((w["l"].min() / e - 1) * 100, 1)
        s0 = d["s_open"]
        otm = None
        if s0 == s0 and s0:
            otm = (s0 - r.strike) / s0 * 100 if r.side == "PE" else (r.strike - s0) / s0 * 100
        gap_head = None if d["gap"] != d["gap"] else (d["gap"] if r.side == "PE" else -d["gap"])
        rows.append({
            "day0": r.day0, "half": d["half"], "symbol": r.symbol, "side": r.side, "strike": r.strike,
            "expiry": r.expiry, "lot": q, "entry": e, "buy value Rs": round(e * q),
            "sessions to expiry": d["sessions_to_expiry"], "strike distance %": None if otm is None else round(otm, 2),
            "opening gap with headline %": None if gap_head is None else round(gap_head, 2),
            "run-up 5d %": d["pre5"], "run-up 20d %": d["pre20"], "net profit YoY %": d["np_yoy"],
            "net profit QoQ %": d["np_qoq"], "revenue YoY %": d["rev_yoy"],
            "v12 why": d["v12 why"], "v12 at": at, "v12 sell": sell, "v12 net Rs": net, "v12 net %": d["v12 net %"],
            "peak high while held (proxy)": pk_hi, "peak at": held.loc[hi_i, "t"],
            "MFE % (high proxy)": round((pk_hi / e - 1) * 100, 1), "MFE % (close proxy)": round((pk_cl / e - 1) * 100, 1),
            "MAE % (low proxy)": round((lo / e - 1) * 100, 1),
            "net at peak Rs (proxy)": round(pn, 2), "left Rs (proxy)": round(pn - net, 2),
            "captured % (proxy)": round(net / pn * 100, 1) if pn > 0 else None,
            "price give-back %": round((pk_hi - sell) / pk_hi * 100, 1),
            "stock fade after open % (post-entry)": d["stock_fade_pct"],
            "v10 net Rs": d["v10 net Rs"], "max up all day %": d["max up %"], **early})
    return pd.DataFrame(rows)


GROUPS = {
    "Entry premium": ("entry", [0, 3, 5, 7, 10, 15, np.inf], ["< Rs 3", "Rs 3-5", "Rs 5-7", "Rs 7-10", "Rs 10-15", ">= Rs 15"]),
    "Strike distance (OTM %)": ("strike distance %", [-np.inf, 0, 1, 2, 3, 5, np.inf],
                                ["in the money", "0-1 %", "1-2 %", "2-3 %", "3-5 %", ">= 5 %"]),
    "Sessions to expiry": ("sessions to expiry", [0, 3, 7, 14, np.inf], ["<= 3", "4-7", "8-14", ">= 15"]),
    "Opening gap with the headline": ("opening gap with headline %", [-np.inf, 0, 2, 5, np.inf],
                                      ["against (< 0)", "0-2 %", "2-5 %", ">= 5 %"]),
}


def group_table(d: pd.DataFrame, label: pd.Series) -> pd.DataFrame:
    out = []
    for g, x in d.groupby(label, observed=True, sort=True):
        out.append({"group": str(g), "trades": len(x), "wins": int((x["v12 net Rs"] > 0).sum()),
                    "win %": round((x["v12 net Rs"] > 0).mean() * 100, 1),
                    "mean net %": round(x["v12 net %"].mean(), 2), "median net %": round(x["v12 net %"].median(), 2),
                    "t": clustered_t(x["v12 net %"], x["day0"]) if len(x) >= 5 else None,
                    "total Rs": round(x["v12 net Rs"].sum()),
                    "mean MFE % (proxy)": round(x["MFE % (high proxy)"].mean(), 1),
                    "mean MAE % (proxy)": round(x["MAE % (low proxy)"].mean(), 1),
                    "median captured % (proxy)": round(x["captured % (proxy)"].median(), 1),
                    "mean net at peak Rs": round(x["net at peak Rs (proxy)"].mean()),
                    "mean realised Rs": round(x["v12 net Rs"].mean()),
                    "stop / trail": f"{(x['v12 why'] == 'stop').sum()} / {(x['v12 why'] == 'trail').sum()}",
                    "train mean %": round(x.loc[x.half == "train", "v12 net %"].mean(), 2),
                    "test mean %": round(x.loc[x.half == "test", "v12 net %"].mean(), 2),
                    "train / test n": f"{(x.half == 'train').sum()} / {(x.half == 'test').sum()}",
                    "note": "inconclusive (< 20)" if len(x) < 20 else ""})
    return pd.DataFrame(out)


def tables(d: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out = {}
    for name, (col, bins, labels) in GROUPS.items():
        lab = pd.cut(d[col], bins, labels=labels, right=False)
        out[name] = group_table(d, lab.cat.add_categories(["missing"]).fillna("missing"))
    for side in ("PE", "CE"):
        x = d[d.side == side]
        lab = pd.qcut(x["net profit YoY %"], 4, labels=["Q1 lowest", "Q2", "Q3", "Q4 highest"])
        out[f"Net profit YoY quartiles ({side})"] = group_table(x, lab)
    stock = pd.cut(d["stock fade after open % (post-entry)"], [-np.inf, -1, 0, 1, np.inf],
                   labels=["ran on > 1 %", "ran on 0-1 %", "faded 0-1 %", "faded > 1 %"], right=False)
    out["Stock after the open (post-entry, explain only)"] = group_table(d, stock)
    early = pd.cut(d["first 3 min max dip %"], [-np.inf, -20, -10, 0, np.inf],
                   labels=["fell >= 20 %", "fell 10-20 %", "fell 0-10 %", "never below entry"], right=False)
    out["First 3 minutes (post-entry, explain only)"] = group_table(d, early)
    return out


def losers(d: pd.DataFrame) -> pd.DataFrame:
    x = d[d["v12 net Rs"] < 0]
    kind = np.select([x["MFE % (high proxy)"] < 2, x["MFE % (high proxy)"] < 10],
                     ["never profitable (peak < +2 %)", "briefly up +2-10 %, then the stop"], "armed the trail (+10 %) and still lost")
    return x.assign(kind=kind).groupby("kind").agg(trades=("symbol", "size"), total_Rs=("v12 net Rs", "sum"),
                                                     mean_MFE=("MFE % (high proxy)", "mean"),
                                                     mean_first3_dip=("first 3 min max dip %", "mean")).round(1).reset_index()


COLS_TOP = ["day0", "symbol", "side", "strike", "entry", "v12 why", "v12 at", "v12 sell", "v12 net Rs",
            "peak high while held (proxy)", "peak at", "MFE % (high proxy)", "net at peak Rs (proxy)", "left Rs (proxy)",
            "captured % (proxy)", "first 1 min max up %", "first 1 min max dip %", "strike distance %",
            "sessions to expiry", "stock fade after open % (post-entry)"]


def main() -> None:
    d = build()
    d.to_csv(RES / "S1_fade_entry_quality_audit_trades.csv", index=False)
    tb = tables(d)
    corr = d[["entry", "strike distance %", "sessions to expiry", "opening gap with headline %", "net profit YoY %",
              "v12 net %", "MFE % (high proxy)"]].corr(method="spearman").round(2)
    top_give = d.sort_values("left Rs (proxy)", ascending=False).head(15)[COLS_TOP]
    top_loss = d.sort_values("v12 net Rs").head(15)[COLS_TOP]
    lz = losers(d)
    cap = d["captured % (proxy)"].dropna()
    head = {"trades": len(d), "v12 total Rs": round(d["v12 net Rs"].sum()),
            "net at peak total Rs (proxy)": round(d["net at peak Rs (proxy)"].clip(lower=0).sum()),
            "left total Rs (proxy)": round(d["left Rs (proxy)"].sum()),
            "median captured % (proxy)": round(cap.median(), 1), "trades with a paying peak": len(cap),
            "median peak at": d["peak at"].median() if False else d["peak at"].mode().iat[0]}
    write_md(d, tb, corr, top_give, top_loss, lz, head)
    write_xlsx(d, tb, corr, top_give, top_loss, lz, head)
    print(head)


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        lines.append("| " + " | ".join("" if (isinstance(v, float) and v != v) or v is None else str(v) for v in r) + " |")
    return "\n".join(lines)


def write_md(d, tb, corr, top_give, top_loss, lz, head) -> None:
    parts = ["# S1 fade · peak capture and entry quality (exploratory, 339 backtest trades)", "",
             "Protocol: `strategies/S1_fade_entry_quality_audit.md`. Entry 09:16 open + 1 tick, v12 exit, real charges. "
             "**Peaks are an OHLC proxy** (1-minute candle highs), not sellable bids; the live best-bid measurement "
             "started on 23 Oct 2026 (`server/peak.py`). Train = before 2025-11-03, test = from it (not pristine).", "",
             "## Headline", "", md_table(pd.DataFrame([head])), ""]
    for name, df in tb.items():
        parts += [f"## {name}", "", md_table(df), ""]
    parts += ["## Losing trades by kind", "", md_table(lz), "",
              "## Correlations (Spearman)", "", md_table(corr.reset_index().rename(columns={"index": ""})), "",
              "## The 15 largest give-backs (proxy)", "", md_table(top_give), "",
              "## The 15 largest losses", "", md_table(top_loss), ""]
    (RES / "S1_fade_entry_quality_audit.md").write_text("\n".join(parts), encoding="utf-8")


def write_xlsx(d, tb, corr, top_give, top_loss, lz, head) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    A = "Arial"
    H, F = Font(name=A, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3A5F")
    T, B = Font(name=A, bold=True, size=13), Font(name=A, size=10)
    thin = Side(style="thin", color="C8C8C8")

    def put(ws, df, r0, title=None, note=None):
        if title:
            ws.cell(r0, 1, title).font = T
            r0 += 1
        if note:
            ws.cell(r0, 1, note).font = Font(name=A, italic=True, size=9, color="555555")
            r0 += 1
        for j, c in enumerate(df.columns, 1):
            x = ws.cell(r0, j, str(c))
            x.font, x.fill = H, F
            x.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.row_dimensions[r0].height = 42
        for i, row in enumerate(df.itertuples(index=False), r0 + 1):
            for j, v in enumerate(row, 1):
                v = None if (isinstance(v, float) and v != v) else (v.item() if hasattr(v, "item") else v)
                x = ws.cell(i, j, v)
                x.font, x.border = B, Border(top=thin, bottom=thin, left=thin, right=thin)
                h = str(df.columns[j - 1])
                if isinstance(v, (int, float)):
                    x.number_format = "#,##0;-#,##0;0" if "Rs" in h else "0.0" if ("%" in h or h == "t") else "General"
        return r0 + len(df) + 2

    def widths(ws, first=34, rest=14):
        for j in range(1, ws.max_column + 1):
            ws.column_dimensions[get_column_letter(j)].width = first if j == 1 else rest

    ws = wb.active
    ws.title = "Summary"
    ws["A1"] = "S1 fade · peak capture and entry quality (exploratory)"
    ws["A1"].font = Font(name=A, bold=True, size=15)
    notes = ["339 backtest trades, Oct 2024 - Aug 2026, v12 exit, entry 09:16 open + 1 tick, real charges.",
             "Peaks on this history are an OHLC PROXY (1-minute candle highs), NOT bids a sell could fill at. "
             "Live best-bid peaks are recorded from 23 Oct 2026.",
             "Captured % uses the MEDIAN: a tiny peak profit in the denominator makes single ratios explode (e.g. -900 %).",
             "Figures are values computed by scanner/fade_entry_quality.py from the 'Trades' sheet "
             "(no live formulas: recalculation was not available here).",
             "Exploratory: no threshold here is a rule. Groups under 20 trades are inconclusive. "
             "Sheets marked 'post-entry' explain outcomes only; they cannot be used as entry filters."]
    for i, n in enumerate(notes, 3):
        ws.cell(i, 1, n).font = B
    r = put(ws, pd.DataFrame([head]), 8, "Headline")
    r = put(ws, lz, r, "Losing trades by kind")
    widths(ws, 34, 18)
    for name, df in tb.items():
        s = wb.create_sheet(name.replace("(", "").replace(")", "").replace(",", "")[:31])
        put(s, df, 1, name, "v12 net % = net % of the premium per trade after charges; MFE / MAE / captured = OHLC proxy; "
                            "t = date-clustered (>= 2 strong); train before 3 Nov 2025, test from it")
        widths(s, 22, 13)
        s.freeze_panes = "B4"
    s = wb.create_sheet("Biggest give-backs")
    put(s, top_give, 1, "The 15 largest give-backs: net at the proxy peak minus the realised net")
    widths(s, 12, 13)
    s = wb.create_sheet("Biggest losses")
    put(s, top_loss, 1, "The 15 largest v12 losses")
    widths(s, 12, 13)
    s = wb.create_sheet("Correlations")
    put(s, corr.reset_index().rename(columns={"index": "Spearman"}), 1, "How the entry features move together",
        "close to 0 = unrelated; +/-0.5 or more = strongly related (then one effect may show up in two groups)")
    widths(s, 30, 16)
    s = wb.create_sheet("Trades")
    put(s, d.sort_values(["day0", "symbol"]), 1)
    widths(s, 12, 13)
    s.freeze_panes = "D2"
    s.auto_filter.ref = s.dimensions
    wb.save(RES / "S1_fade_entry_quality_audit.xlsx")


if __name__ == "__main__":
    main()
