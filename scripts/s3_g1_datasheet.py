"""G1 datasheet for the user to look for optimisations (the user, 2026-11-04: "give me the datasheet let me figure out
whether there is something help us to optimize"). One row per G1 trade (2024-10 → 2026-10, in-sample) with what was
known at entry, what happened after, and every variant's result side by side. Writes data/results/S3_G1_datasheet.xlsx.

    INDEX_STORE=<index-data checkout>/data/index python scripts/s3_g1_datasheet.py
"""
from datetime import date, time

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from index_data import load as L
from scanner.s3_b2 import signal
from scanner.s3_pods import RES

FONT = "Arial"
src = pd.read_csv(RES / "S3_PUT1_hold_trades.csv")
src = src[src["skip"].fillna("") == ""]
g1 = src[src["variant"] == "G1"].copy()
other = src.pivot_table(index="day", columns="variant", values="net_pct_premium")
stops = pd.read_csv(RES / "S3_G1_stops_trades.csv")         # G1 with other stops (the user: "keep the sl of 20%")
stops = stops[stops["skip"].fillna("") == ""].pivot_table(index="day", columns="variant", values="net_pct_premium")
STOPS = {"S20": "G1 stop 20 % net %", "S25": "G1 stop 25 % net %", "S30": "G1 stop 30 % net %",
         "S40": "G1 stop 40 % net %", "none": "G1 no stop net %"}

sp = L.spot_1m(date(2024, 8, 1), date(2026, 11, 10), "NIFTY50")
sp["d"] = sp["timestamp"].dt.date
days = {d: g.reset_index(drop=True) for d, g in sp.groupby("d") if len(g) >= 300}
ses = sorted(days)
close = pd.Series({d: float(days[d]["close"].iloc[-1]) for d in ses})
ema20 = close.ewm(span=20, adjust=False).mean()
vx = L.vix_1m(date(2024, 9, 1), date(2026, 11, 10))
vx["d"] = vx["timestamp"].dt.date
vix_open = vx.groupby("d")["open"].first()
vix_close = vx.groupby("d")["close"].last()


def at(g, hh, mm):
    x = g[g["timestamp"].dt.time <= time(hh, mm)]
    return float(x["close"].iloc[-1]) if len(x) else np.nan


rows = []
for r in g1.sort_values("day").itertuples():
    d = date.fromisoformat(r.day)
    i = ses.index(d)
    g = days[d]
    t = g["timestamp"].dt.time
    rng = g[(t >= time(9, 15)) & (t < time(9, 30))]
    hi, lo = rng["high"].max(), rng["low"].min()
    sg = signal(g, 15, None)
    sh, sm = sg[1].hour, sg[1].minute
    assert sg[0] == "PE" and (sg[1] + pd.Timedelta(minutes=1)).strftime("%H:%M") == r.entry
    eh, em = map(int, r.entry.split(":"))
    sig_close = at(g, sh, sm)
    ent_spot = at(g, eh, em)
    after = g[g["timestamp"].dt.time >= time(eh, em)]
    prev = ses[i - 1]
    nxt = ses[i + 1] if i + 1 < len(ses) else None
    g2 = days.get(nxt)
    vxd = vx[vx["d"] == d]
    vix_sig = vxd[vxd["timestamp"].dt.time <= time(sh, sm)]["close"]
    rows.append({
        "Day": d, "Weekday": d.strftime("%a"), "Month": d.strftime("%Y-%m"),
        "Expiry": date.fromisoformat(r.expiry), "Days to expiry": int(r.dte),
        "Signal time": sg[1].strftime("%H:%M"), "Minutes after 09:30": (sh - 9) * 60 + sm - 30, "Entry time": r.entry,
        "Spot at entry": ent_spot, "Strike": float(r.atm),
        "OR high": hi, "OR low": lo, "OR width %": (hi - lo) / lo * 100,
        "Breakout depth at signal %": (lo - sig_close) / lo * 100,
        "Day-1 gap at open %": (float(g["open"].iloc[0]) / close[prev] - 1) * 100,
        "Day-1 open → entry %": (ent_spot / float(g["open"].iloc[0]) - 1) * 100,
        "Prev day return %": (close[prev] / close[ses[i - 2]] - 1) * 100,
        "Prev 5-day return %": (close[prev] / close[ses[i - 6]] - 1) * 100,
        "Prev close vs EMA20 %": (close[prev] / ema20[prev] - 1) * 100,
        "VIX at signal": float(vix_sig.iloc[-1]) if len(vix_sig) else np.nan,
        "VIX change since open": (float(vix_sig.iloc[-1]) - float(vix_open.get(d, np.nan))) if len(vix_sig) else np.nan,
        "VIX prev close": float(vix_close.get(prev, np.nan)),
        "Premium paid (₹/unit)": float(r.premium), "Premium (₹/lot)": float(r.premium_rs),
        "Premium % of spot": float(r.premium) / ent_spot * 100, "Lot": int(r.qty),
        "Day-1 entry → 15:15 %": (at(g, 15, 15) / ent_spot - 1) * 100,
        "Day-1 low after entry %": (after["low"].min() / ent_spot - 1) * 100,
        "Day-1 high after entry %": (after["high"].max() / ent_spot - 1) * 100,
        "Day-1 15:15 vs OR low %": (at(g, 15, 15) / lo - 1) * 100,
        "Next-day gap %": float(r.gap_pct) if pd.notna(r.gap_pct) else np.nan,
        "Next-day open → 15:15 %": ((at(g2, 15, 15) / float(g2["open"].iloc[0]) - 1) * 100) if g2 is not None else np.nan,
        "G1 exit": "stop" if r.reason == "stop" else "next open", "G1 exit day": date.fromisoformat(r.exit_day),
        "G1 exit time": r.exit_at, "G1 net %": float(r.net_pct_premium), "G1 net ₹": float(r.net_rs),
        "G1 charges ₹": float(r.fees_rs), "G1 max up held %": float(r.max_up_pct),
        "PUT1 15:15 no stop %": other.loc[r.day, "P0"], "50 % stop, 15:15 %": other.loc[r.day, "P1"],
        "Next day 15:15 %": other.loc[r.day, "P2"], "Next-day breakout rule %": other.loc[r.day, "P3"],
        "Gap down keep %": other.loc[r.day, "G2"], "Gap down sell %": other.loc[r.day, "G3"],
        **{v: stops.loc[r.day, k] for k, v in STOPS.items()},
    })
df = pd.DataFrame(rows)
df.to_csv(RES / "S3_G1_datasheet.csv", index=False)

# ---------- workbook (the user, 2026-11-04: "make the g1 result in front ... make the excel optimizr") ----------
from openpyxl.worksheet.datavalidation import DataValidation

FRONT = ["Day", "G1 net %", "G1 net ₹", "G1 exit", "G1 max up held %", "Premium (₹/lot)"]
ENTRY = ["Days to expiry", "Minutes after 09:30", "OR width %", "Breakout depth at signal %", "Day-1 gap at open %",
         "Day-1 open → entry %", "Prev day return %", "Prev 5-day return %", "Prev close vs EMA20 %", "VIX at signal",
         "VIX change since open", "VIX prev close", "Premium paid (₹/unit)", "Premium % of spot", "Spot at entry",
         "Day-1 15:15 vs OR low %"]                      # numeric, known at entry (the last one at 15:15 on day 1)
OPT = ["Opt lots", "Opt net ₹", "Opt paid ₹", "Opt net % if taken", "Opt equity ₹", "Opt peak ₹", "Opt drawdown ₹"]
REST = [c for c in df.columns if c not in FRONT and c not in ENTRY]
RULES = [("OR width %", "Yes", 0.5, 0.8, "Skip"), ("Day-1 gap at open %", "Yes", 0.3, None, "Skip"),
         ("VIX at signal", "Yes", 17, None, "Skip"), ("Minutes after 09:30", "No", 15, 120, "Double"),
         ("VIX at signal", "No", 12, 14, "Double"), ("Days to expiry", "No", None, None, "Skip"),
         (None, "No", None, None, "Skip"), (None, "No", None, None, "Skip")]
NR = len(RULES)
cols = FRONT + OPT + ENTRY + REST + [f"Rule {k + 1}" for k in range(NR)]
col = {c: get_column_letter(i + 1) for i, c in enumerate(cols)}
LASTC = get_column_letter(len(cols))
E0, E1 = col[ENTRY[0]], col[ENTRY[-1]]                 # the block the rules may look up (no circular reference)

wb = Workbook()
HDR = PatternFill("solid", fgColor="1F3864")
YEL = PatternFill("solid", fgColor="FFFF00")
GRP = {"G1 result": "FFF2CC", "Optimizer (formulas)": "DDEBF7", "Known at entry": "E2EFDA",
       "After entry (hindsight)": "FCE4D6", "Other variants": "EDEDED", "Optimizer helpers": "F2F2F2",
       "Trade details": "FFFFFF"}
thin = Side(style="thin", color="BFBFBF")
B = Border(left=thin, right=thin, top=thin, bottom=thin)
pct = '+0.00"%";-0.00"%";0.00"%"'
pct1 = '+0.0"%";-0.0"%";0.0"%"'
rs = '"₹"#,##0;[Red]-"₹"#,##0'
fmt = {"Day": "yyyy-mm-dd", "Expiry": "yyyy-mm-dd", "G1 exit day": "yyyy-mm-dd", "Spot at entry": "#,##0.00",
       "Strike": "#,##0", "OR high": "#,##0.00", "OR low": "#,##0.00", "VIX at signal": "0.00",
       "VIX change since open": "+0.00;-0.00;0.00", "VIX prev close": "0.00", "Premium paid (₹/unit)": '"₹"#,##0.00',
       "Premium (₹/lot)": rs, "G1 net ₹": rs, "G1 charges ₹": rs, "Lot": "0", "Days to expiry": "0",
       "Minutes after 09:30": "0", "Opt lots": "0"}
VARS = ["PUT1 15:15 no stop %", "50 % stop, 15:15 %", "Next day 15:15 %", "Next-day breakout rule %",
        "Gap down keep %", "Gap down sell %", *STOPS.values()]


def grp(c):
    if c in OPT:
        return "Optimizer (formulas)"
    if c.startswith("Rule "):
        return "Optimizer helpers"
    if c in VARS:
        return "Other variants"
    if c in FRONT or c.startswith("G1 "):
        return "G1 result"
    if c in ENTRY or c in ("Weekday", "Month"):
        return "Known at entry"
    if c.startswith(("Day-1 entry", "Day-1 low", "Day-1 high", "Next-day")):
        return "After entry (hindsight)"
    return "Trade details"


def number_format(c):
    if c in fmt:
        return fmt[c]
    if c.endswith("₹"):
        return rs
    if c.endswith("%"):
        return pct1 if ("net" in c or "max up" in c or c in VARS) else pct
    return "General"


notes = {
    "Days to expiry": "Sessions left after the signal day up to and including expiry.",
    "Breakout depth at signal %": "How far the signal minute closed below the opening-range low.",
    "Prev close vs EMA20 %": "Previous close against its 20-day EMA. Negative = downtrend.",
    "Next-day gap %": "Next session's 09:15 open against day 1's last close. What GIFT Nifty shows by 09:00. Not known at entry.",
    "G1 net %": "Net after slippage (0.5 %, 1 % before 09:30) and charges, % of premium paid.",
    "G1 max up held %": "Best minute close of the put while held, % above the price paid.",
    "Day-1 15:15 vs OR low %": "Known at 15:15 on day 1 (when the overnight hold is decided), not at entry.",
    "Opt lots": "Lots the Optimizer sheet's active rules give this trade: 0 = skipped.",
    "Gap down keep %": "G2: gap down → keep by the next-day breakout rule; gap up → sell at the open.",
    "Gap down sell %": "G3: gap down → sell at the open; gap up → keep by the next-day breakout rule.",
    "Next-day breakout rule %": "P3: next day's first breakout down → hold to 15:15; up → sell next minute; none by 13:00 → 13:16.",
}

ws = wb.active
ws.title = "Summary"
op = wb.create_sheet("Optimizer")
tr = wb.create_sheet("Trades")
lists = wb.create_sheet("Lists")
n = len(df)
first, last = 3, n + 2
for i, c in enumerate(cols, 1):
    g_ = grp(c)
    gcell = tr.cell(row=1, column=i, value=g_)
    gcell.fill = PatternFill("solid", fgColor=GRP[g_])
    gcell.font = Font(name=FONT, bold=True, size=9)
    h = tr.cell(row=2, column=i, value=c)
    h.fill, h.font, h.border = HDR, Font(name=FONT, bold=True, color="FFFFFF"), B
    h.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    if c in notes:
        h.comment = Comment(notes[c], "Claude")
    tr.column_dimensions[get_column_letter(i)].width = 8 if c.startswith("Rule ") else max(11, min(16, len(c) * 0.75 + 4))
tr.row_dimensions[2].height = 45

O = "Optimizer"
for ri, row in enumerate(df.itertuples(index=False), first):
    vals = dict(zip(df.columns, row))
    for c in cols:
        if c in vals:
            v = vals[c]
            v = None if isinstance(v, float) and np.isnan(v) else v
        elif c.startswith("Rule "):
            k = int(c.split()[1]) + 3                       # rule rows are rows 4.. of the Optimizer sheet
            look = f"INDEX(${E0}{ri}:${E1}{ri},MATCH({O}!$A${k},${E0}$2:${E1}$2,0))"
            lo_ = f'IF({O}!$C${k}="",-1E+99,{O}!$C${k})'
            hi_ = f'IF({O}!$D${k}="",1E+99,{O}!$D${k})'
            v = (f'=IF(OR({O}!$B${k}<>"Yes",{O}!$A${k}=""),"",IF(ISNUMBER({look}),IF(AND({look}>={lo_},{look}<{hi_}),'
                 f'IF({O}!$E${k}="Double","D","S"),""),""))')
        elif c == "Opt lots":
            rr = f"${col['Rule 1']}{ri}:${col[f'Rule {NR}']}{ri}"
            v = f'=IF(COUNTIF({rr},"S")>0,0,IF(COUNTIF({rr},"D")>0,{O}!$B$15,{O}!$B$14))'
        elif c == "Opt net ₹":
            v = f"={col['Opt lots']}{ri}*{col['G1 net ₹']}{ri}"
        elif c == "Opt paid ₹":
            v = f"={col['Opt lots']}{ri}*{col['Premium (₹/lot)']}{ri}"
        elif c == "Opt net % if taken":
            v = f'=IF({col["Opt lots"]}{ri}>0,{col["G1 net %"]}{ri},"")'
        elif c == "Opt equity ₹":
            v = f"={col['Opt net ₹']}{ri}" + (f"+{col['Opt equity ₹']}{ri - 1}" if ri > first else "")
        elif c == "Opt peak ₹":
            v = (f"=MAX({col['Opt peak ₹']}{ri - 1},{col['Opt equity ₹']}{ri})" if ri > first
                 else f"=MAX(0,{col['Opt equity ₹']}{ri})")
        else:                                              # Opt drawdown ₹
            v = f"={col['Opt equity ₹']}{ri}-{col['Opt peak ₹']}{ri}"
        cell = tr[f"{col[c]}{ri}"]
        cell.value = v
        cell.font = Font(name=FONT, size=10)
        cell.border = B
        cell.number_format = number_format(c)
        if c == "G1 net %" and v is not None:
            cell.font = Font(name=FONT, size=10, bold=True, color="006100" if v > 0 else "9C0006")
        if c == "Opt lots":
            cell.font = Font(name=FONT, size=10, bold=True, color="1F3864")
tr.freeze_panes = f"{col['Opt lots']}3"              # Day and the G1 result stay in view while scrolling
tr.auto_filter.ref = f"A2:{LASTC}{last}"
R = lambda c: f"Trades!${col[c]}${first}:${col[c]}${last}"

for i, c in enumerate(ENTRY, 1):
    lists.cell(row=i, column=1, value=c)
for i, c in enumerate(("Yes", "No"), 1):
    lists.cell(row=i, column=2, value=c)
for i, c in enumerate(("Skip", "Double"), 1):
    lists.cell(row=i, column=3, value=c)
lists.sheet_state = "hidden"

# ---------- Optimizer sheet ----------
for c, w in zip("ABCDEFGHI", (30, 10, 11, 11, 11, 3, 36, 16, 18)):
    op.column_dimensions[c].width = w
op["A1"] = "G1 optimizer · switch filters on and off and see the result"
op["A1"].font = Font(name=FONT, bold=True, size=14, color="1F3864")
op["A2"] = ("Edit the yellow cells. A trade is skipped if any active Skip rule matches (From ≤ value < To; a blank "
            "edge means no limit); otherwise it gets the doubled lots if any active Double rule matches. Only columns "
            "known at entry are offered. In-sample: anything found here must be pre-registered and tested forward.")
op["A2"].font = Font(name=FONT, italic=True, size=9)
op["A2"].alignment = Alignment(wrap_text=True, vertical="top")
op.merge_cells("A2:I2")
op.row_dimensions[2].height = 40


def ohead(r, c0, labels):
    for j, t in enumerate(labels):
        c = op.cell(row=r, column=c0 + j, value=t)
        c.fill, c.font, c.border = HDR, Font(name=FONT, bold=True, color="FFFFFF"), B
        c.alignment = Alignment(horizontal="center", wrap_text=True)


def ocell(r, c, v, f="General", bold=False, inp=False):
    x = op.cell(row=r, column=c, value=v)
    x.font = Font(name=FONT, bold=bold, color="0000FF" if inp else None)
    x.border, x.number_format = B, f
    if inp:
        x.fill = YEL
    return x


ohead(3, 1, ["Rule: column", "Active", "From ≥", "To <", "Action"])
for k, (c, a, lo, hi, act) in enumerate(RULES, 4):
    for j, (v, f) in enumerate(((c, "General"), (a, "General"), (lo, "0.00"), (hi, "0.00"), (act, "General")), 1):
        ocell(k, j, v, f, inp=True)
for dv, rng in ((DataValidation(type="list", formula1=f"=Lists!$A$1:$A${len(ENTRY)}", allow_blank=True), f"A4:A{3 + NR}"),
                (DataValidation(type="list", formula1="=Lists!$B$1:$B$2"), f"B4:B{3 + NR}"),
                (DataValidation(type="list", formula1="=Lists!$C$1:$C$2"), f"E4:E{3 + NR}")):
    op.add_data_validation(dv)
    dv.add(rng)
assert 3 + NR < 13
op.cell(row=13, column=1, value="Lot sizes").font = Font(name=FONT, bold=True)
ocell(14, 1, "Lots on a normal trade")
ocell(14, 2, 1, "0", inp=True)
ocell(15, 1, "Lots when a Double rule matches")
ocell(15, 2, 2, "0", inp=True)
ocell(17, 1, "Preset: rules 1-3 on = G1-F (registered for the forward test). Turn all off = G1.").font = Font(name=FONT, italic=True, size=9)

lots, onet, opaid, opct = R("Opt lots"), R("Opt net ₹"), R("Opt paid ₹"), R("Opt net % if taken")
gnet, gpct, gpaid, day = R("G1 net ₹"), R("G1 net %"), R("Premium (₹/lot)"), R("Day")
ohead(3, 7, ["Result", "Optimized", "G1 as registered"])
Y2 = "DATE(2025,10,1)"
res = [("Trades taken", f'COUNTIF({lots},">0")', f"COUNT({gpct})", "0"),
       ("Lots", f"SUM({lots})", f"COUNT({gpct})", "0"),
       ("Total net ₹", f"SUM({onet})", f"SUM({gnet})", rs),
       ("Return on ₹ paid", f"SUM({onet})/SUM({opaid})", f"SUM({gnet})/SUM({gpaid})", "+0.0%;-0.0%"),
       ("Mean net % a trade", f"AVERAGE({opct})", f"AVERAGE({gpct})", pct1),
       ("Median net % a trade", f"MEDIAN({opct})", f"MEDIAN({gpct})", pct1),
       ("t (mean ÷ standard error)", f"AVERAGE({opct})/(STDEV({opct})/SQRT(COUNT({opct})))",
        f"AVERAGE({gpct})/(STDEV({gpct})/SQRT(COUNT({gpct})))", "0.00"),
       ("Win rate", f'COUNTIF({opct},">0")/COUNT({opct})', f'COUNTIF({gpct},">0")/COUNT({gpct})', "0.0%"),
       ("Worst trade ₹", f"MIN({onet})", f"MIN({gnet})", rs),
       ("Best trade ₹", f"MAX({onet})", f"MAX({gnet})", rs),
       ("Max drawdown ₹", f"MIN({R('Opt drawdown ₹')})", None, rs),
       ("Year 1 return on ₹ paid (to 2025-09)", f'SUMIFS({onet},{day},"<"&{Y2})/SUMIFS({opaid},{day},"<"&{Y2})',
        f'SUMIFS({gnet},{day},"<"&{Y2})/SUMIFS({gpaid},{day},"<"&{Y2})', "+0.0%;-0.0%"),
       ("Year 2 return on ₹ paid (from 2025-10)", f'SUMIFS({onet},{day},">="&{Y2})/SUMIFS({opaid},{day},">="&{Y2})',
        f'SUMIFS({gnet},{day},">="&{Y2})/SUMIFS({gpaid},{day},">="&{Y2})', "+0.0%;-0.0%")]
for k, (lab, f1, f2, nf) in enumerate(res, 4):
    ocell(k, 7, lab)
    ocell(k, 8, f'=IFERROR({f1},"")', nf, bold=True)
    if f2:
        ocell(k, 9, f'=IFERROR({f2},"")', nf)
    else:                                  # G1's drawdown is fixed (its lots never change): computed here
        eq = df["G1 net ₹"].cumsum()
        ocell(k, 9, round(float((eq - eq.cummax().clip(lower=0)).min()), 2), nf).comment = Comment(
            "G1 as registered never changes, so this one is a fixed value computed in Python.", "Claude")
op.freeze_panes = "A4"

# ---------- Summary sheet ----------
ws.column_dimensions["A"].width = 34
for c in "BCDEFGH":
    ws.column_dimensions[c].width = 14
ws["A1"] = "S3 G1 datasheet · NIFTY downside ORB put, held overnight, sold at the next open"
ws["A1"].font = Font(name=FONT, bold=True, size=14, color="1F3864")
ws["A2"] = ("In-sample, 2024-10-01 → 2026-10-28, real NIFTY option minutes. Best of 7 variants on the same data, so "
            "flattered. Optimizer sheet: switch filters and see the result. Trades sheet: the G1 result first, green "
            "columns known at entry, orange ones hindsight.")
ws["A2"].font = Font(name=FONT, italic=True, size=9)
ws["A2"].alignment = Alignment(wrap_text=True)
ws.merge_cells("A2:H2")
ws.row_dimensions[2].height = 30


def head(r, labels):
    for j, t in enumerate(labels):
        c = ws.cell(row=r, column=1 + j, value=t)
        c.fill, c.font, c.border = HDR, Font(name=FONT, bold=True, color="FFFFFF"), B
        c.alignment = Alignment(horizontal="center", wrap_text=True)


def put(r, j, v, f="General", bold=False):
    c = ws.cell(row=r, column=j, value=v)
    c.font, c.border, c.number_format = Font(name=FONT, bold=bold), B, f
    return c


head(4, ["Statistic", "Value"])
net, nrs, mu = R("G1 net %"), R("G1 net ₹"), R("G1 max up held %")
stats = [("Trades", f"=COUNT({net})", "0"), ("Mean net %", f"=AVERAGE({net})", pct1),
         ("Median net %", f"=MEDIAN({net})", pct1), ("Std deviation %", f"=STDEV({net})", pct1),
         ("t (mean ÷ standard error)", f"=B6/(B8/SQRT(B5))", "0.00"),
         ("Win rate", f"=COUNTIF({net},\">0\")/B5", "0.0%"),
         ("Average win %", f"=AVERAGEIF({net},\">0\")", pct1), ("Average loss %", f"=AVERAGEIF({net},\"<=0\")", pct1),
         ("Payoff (win ÷ loss)", "=-B11/B12", "0.00\"x\""),
         ("Profit factor (₹)", f"=SUMIF({nrs},\">0\")/-SUMIF({nrs},\"<0\")", "0.00"),
         ("Total net ₹", f"=SUM({nrs})", rs), ("Average trade ₹", f"=AVERAGE({nrs})", rs),
         ("Worst trade ₹", f"=MIN({nrs})", rs), ("Best trade ₹", f"=MAX({nrs})", rs),
         ("Max up held: mean %", f"=AVERAGE({mu})", pct1), ("Max up held: median %", f"=MEDIAN({mu})", pct1),
         ("Max up held ≥ +100 %: share", f"=COUNTIF({mu},\">=100\")/B5", "0.0%"),
         ("Stopped trades", f"=COUNTIF({R('G1 exit')},\"stop\")", "0")]
for k, (lab, f, nf) in enumerate(stats, 5):
    put(k, 1, lab)
    put(k, 2, f, nf, bold=True)
r0 = 5 + len(stats) + 1


def bucket_table(r, title, colname, edges, labels, note):
    ws.cell(row=r, column=1, value=title).font = Font(name=FONT, bold=True, size=12, color="1F3864")
    ws.cell(row=r + 1, column=1, value=note).font = Font(name=FONT, italic=True, size=9)
    head(r + 2, ["Bucket", "From ≥", "To <", "Trades", "Mean net %", "Win rate", "Total ₹", "Max up median %"])
    x = R(colname)
    for k, (lab, (a, b)) in enumerate(zip(labels, edges)):
        rr = r + 3 + k
        put(rr, 1, lab)
        put(rr, 2, a, "0.00").font = Font(name=FONT, color="0000FF")
        put(rr, 3, b, "0.00").font = Font(name=FONT, color="0000FF")
        put(rr, 4, f'=COUNTIFS({x},">="&B{rr},{x},"<"&C{rr})', "0")
        put(rr, 5, f'=IFERROR(AVERAGEIFS({net},{x},">="&B{rr},{x},"<"&C{rr}),"")', pct1, bold=True)
        put(rr, 6, f'=IFERROR(COUNTIFS({x},">="&B{rr},{x},"<"&C{rr},{net},">0")/D{rr},"")', "0.0%")
        put(rr, 7, f'=SUMIFS({nrs},{x},">="&B{rr},{x},"<"&C{rr})', rs)
        # median via AGGREGATE is Excel-2010; LibreOffice lacks it, so the bucket median is computed in Python
        sub = df[(df[colname] >= a) & (df[colname] < b)]["G1 max up held %"]
        put(rr, 8, round(float(sub.median()), 1) if len(sub) else None, pct1).font = Font(name=FONT, color="0000FF")
    return r + 3 + len(labels) + 1


BIG = 1e9
tables = [
    ("By days to expiry", "Days to expiry", [(1, 2), (2, 3), (3, 4), (4, BIG)], ["1", "2", "3", "4+"],
     "Known at entry."),
    ("By signal time (minutes after 09:30)", "Minutes after 09:30", [(0, 15), (15, 60), (60, 120), (120, BIG)],
     ["09:30-09:44", "09:45-10:29", "10:30-11:29", "11:30-13:00"], "Known at entry."),
    ("By opening-range width %", "OR width %", [(0, 0.3), (0.3, 0.5), (0.5, 0.8), (0.8, BIG)],
     ["< 0.3 %", "0.3-0.5 %", "0.5-0.8 %", "≥ 0.8 %"], "Known at entry: (OR high − OR low) ÷ OR low."),
    ("By VIX at signal", "VIX at signal", [(0, 12), (12, 14), (14, 17), (17, BIG)],
     ["< 12", "12-14", "14-17", "≥ 17"], "Known at entry."),
    ("By trend (prev close vs EMA20 %)", "Prev close vs EMA20 %", [(-BIG, -2), (-2, 0), (0, 2), (2, BIG)],
     ["< −2 %", "−2 to 0 %", "0 to +2 %", "≥ +2 %"], "Known at entry. Negative = below the 20-day average."),
    ("By day-1 opening gap %", "Day-1 gap at open %", [(-BIG, -0.3), (-0.3, 0), (0, 0.3), (0.3, BIG)],
     ["< −0.3 %", "−0.3 to 0 %", "0 to +0.3 %", "≥ +0.3 %"], "Known at entry."),
    ("By premium % of spot", "Premium % of spot", [(0, 0.3), (0.3, 0.5), (0.5, 0.8), (0.8, BIG)],
     ["< 0.3 %", "0.3-0.5 %", "0.5-0.8 %", "≥ 0.8 %"], "Known at entry: how expensive the put was."),
    ("By day-1 15:15 vs OR low % (hindsight at entry, known at 15:15)", "Day-1 15:15 vs OR low %",
     [(-BIG, -0.5), (-0.5, 0), (0, BIG)], ["< −0.5 %", "−0.5 to 0 %", "≥ 0 (back above)"],
     "Known by 15:15 on day 1, so it could decide whether to hold overnight."),
    ("By next-day gap % (hindsight: not known at 15:15)", "Next-day gap %", [(-BIG, -0.25), (-0.25, 0), (0, 0.25), (0.25, BIG)],
     ["< −0.25 %", "−0.25 to 0 %", "0 to +0.25 %", "≥ +0.25 %"], "What GIFT Nifty would show by 09:00."),
]
r = r0
for t in tables:
    r = bucket_table(r, *t)
put(r, 1, "Buckets: blue cells are editable edges; change them and the row recalculates (max up median is fixed).").font = Font(name=FONT, italic=True, size=9)
r += 2
ws.cell(row=r, column=1, value="Variants on the same 259 days").font = Font(name=FONT, bold=True, size=12, color="1F3864")
head(r + 1, ["Variant", "Mean net %", "Median %", "Win rate"])
for k, c in enumerate(["G1 net %", "PUT1 15:15 no stop %", "50 % stop, 15:15 %", "Next day 15:15 %",
                       "Next-day breakout rule %", "Gap down keep %", "Gap down sell %", *STOPS.values()]):
    rr = r + 2 + k
    put(rr, 1, c[:-2] if c.endswith(" %") else c)
    put(rr, 2, f"=AVERAGE({R(c)})", pct1, bold=True)
    put(rr, 3, f"=MEDIAN({R(c)})", pct1)
    put(rr, 4, f"=COUNTIF({R(c)},\">0\")/COUNT({R(c)})", "0.0%")
ws.freeze_panes = "A4"
for row in ws.iter_rows():
    for c in row:
        if c.font and c.font.name != FONT:
            c.font = Font(name=FONT, bold=c.font.bold, italic=c.font.italic, color=c.font.color, size=c.font.size)
out = RES / "S3_G1_datasheet.xlsx"
wb.save(out)
print(out, n, "trades")
