"""Excel writer for scanner.fade_live_retest: Summary first, then one sheet per test."""
from __future__ import annotations

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment

from .fade_indicators_xlsx import F, FB, sheet

STOPS = ["stop −20 %", "stop −25 %", "stop −30 %", "stop −40 %", "no stop"]
BOOK = "today's book · "
TB_FROM, TB_BUY = "today's book from", "today's-book buy"
TB_FAIL, TB_MEAN, TB_RS = "today's book: fail %", "today's book: mean net %", "today's book: total Rs"
NAMED = {
    "RSI back above 30 + above EMA 50": "opt RSI back above 30 (after < 30) + opt above EMA 50",
    "range high + Nifty RSI + after 12:30": "opt above the 09:15 – 09:29 range high + Nifty RSI with the trade + clock 12:30 or later",
    "EMA 9 + Supertrend 7×2 turned up + crossed VWAP": "opt above EMA 9 + opt Supertrend 7×2 just turned up + opt just crossed above VWAP",
    "Supertrend 7×2 turned up + stock past VWAP": "opt Supertrend 7×2 just turned up + stock past VWAP with the trade",
}


def stops_table(rep: pd.DataFrame) -> pd.DataFrame:
    out = []
    for lab, pre in (("as booked (live fill)", ""), ("today's book", BOOK)):
        for nm in STOPS:
            x = rep[f"{pre}{nm} · net %"]
            out.append({"fill": lab, "exit": nm, "trades": len(x), "fail %": (x < 0).mean() * 100, "mean net %": x.mean(),
                        "median net %": x.median(), "total Rs": rep[f"{pre}{nm} · net Rs"].sum(),
                        "sold by the stop %": (rep[f"{pre}{nm} · why"] == "stop").mean() * 100,
                        "sold by the trail %": (rep[f"{pre}{nm} · why"] == "trail").mean() * 100})
    return pd.DataFrame(out)


def named(per: list, keys: list[str]) -> pd.DataFrame:
    pos = {k: i for i, k in enumerate(keys)}
    rows = []
    for p in per:
        row = {"trade": p["trade"], "09:16 bought at": p["09:16 bought at"], "09:16 ask": p["09:16 ask"], "09:16 buy · net %": p["09:16 net %"]}
        for lab, key in NAMED.items():
            i = pos[key]
            row[f"{lab} · bought at"], row[f"{lab} · net %"] = p["when"][i], p["net"][i]
        rows.append(row)
    return pd.DataFrame(rows)


def write(path, tr, rep, mx, dm, pat, bs, per, rt, rinfo, md, probs) -> None:
    st = stops_table(rep)
    nm = named(per, list(rt["entry rule"]))
    live_mean, live_rs = tr["live net %"].mean(), tr["live net Rs"].sum()
    bk = rep[f"{BOOK}stop −20 % · net %"]
    old = rep[rep["live buy on the old book"] == "yes"]
    match = int((rep["replay matches live"] == "same price").sum())
    near = int((rep["replay matches live"] == "within 3 points").sum())
    gap = rep["replay − live (points)"].abs()
    lines = [("S1 fade · the past studies re-run on the live websocket data", FB),
             (f"{len(tr)} live fade trades on {tr['day'].nunique()} days ({tr['day'].min()} – {tr['day'].max()}), the only days with a websocket "
              f"1-second file. As booked: fail {(tr['live net %'] < 0).mean() * 100:.0f} %, mean {live_mean:+.2f} %, ₹{live_rs:,.0f}. "
              f"On today's book (see 0): fail {(bk < 0).mean() * 100:.0f} %, mean {bk.mean():+.2f} %, median {bk.median():+.1f} %, "
              f"₹{rep[f'{BOOK}stop −20 % · net Rs'].sum():,.0f}. A reality check on few trades and 4 days, not a verdict.", F), ("", F),
             ("0 · Old-book fills at the open", FB),
             (f"For a few seconds after 09:15 the websocket repeats the previous session's last bid / ask while trades print elsewhere. "
              f"{len(old)} of {len(tr)} live buys were filled on that old ask: "
              + "; ".join(f"{r['symbol']} {r['buy']:.2f} (today's book from {r[TB_FROM]}, first ask {r[TB_BUY]:.2f})"
                          for _, r in old.iterrows())
              + ". A real order could not have filled there (a buy limit above the market fills lower; one below it does not fill). "
              "'Today's book' re-makes those buys at the first today's-book ask with spread ≤ 10 %; the rest are unchanged.", F),
             ("", F), ("1 · Live vs replay (as booked)", FB),
             (f"v12 replayed on the 1-second bid from each live fill gives the live sale price on {match} of {len(rep)} trades and is within "
              f"3 points on {near} more (median gap {gap.median():.1f} points, largest {gap.max():.1f}): replay mean "
              f"{rep['stop −20 % · net %'].mean():+.2f} % vs live {live_mean:+.2f} %. The exit code and the recording agree.", F),
             ("", F), ("2 · Wider stops (1-second bid)", FB)]
    for _, r in st.iterrows():
        lines.append((f"   {r['fill']}, {r['exit']}: fail {r['fail %']:.0f} %, mean {r['mean net %']:+.2f} %, median {r['median net %']:+.1f} %, "
                      f"₹{r['total Rs']:,.0f}, sold by the stop {r['sold by the stop %']:.0f} %", F))
    lines += [("", F), ("3 · Max up / max dip from the today's-book buy (median)", FB),
              (f"   While held: max up {mx['held max up % (last)'].median():.0f} % (bid {mx['held max up % (bid)'].median():.0f} %), max dip "
               f"{mx['held max dip % (last)'].median():.0f} % (bid {mx['held max dip % (bid)'].median():.0f} %). After the sale on day 0 (to 15:30): max up "
               f"{mx['after sale, day 0 max up % (last)'].median():.0f} %. Overall (later sessions to {max(tr['day'])}, Upstox minutes): max up "
               f"{mx['overall max up % (last)'].median():.0f} %, max dip {mx['overall max dip % (last)'].median():.0f} %. "
               f"The overall peak came after the sale on {(mx['overall max up % (last)'] > mx['held max up % (last)'] + 1e-9).mean() * 100:.0f} % of trades.", F),
              ("", F), ("4 · Market pattern", FB)]
    for _, r in dm.iterrows():
        lines.append((f"   {r['day']}: Nifty previous day {r['nifty prev day %']:+.3f} %, gap {r['nifty gap %']:+.2f} %"
                      f"{' → Nifty up yesterday + gap down' if r['pattern'] else ''}", F))
    for _, r in pat.iterrows():
        lines.append((f"   {r['group']}: {int(r['trades'])} trades on {int(r['days'])} day(s); as booked fail {r['as booked: fail %']:.0f} %, mean "
                      f"{r['as booked: mean net %']:+.2f} %; today's book fail {r[TB_FAIL]:.0f} %, mean {r[TB_MEAN]:+.2f} %, "
                      f"₹{r[TB_RS]:,.0f}", F))
    lines += [("   The pattern day is one day: it agrees with the backtest (those days fail more) but cannot confirm it. 28 Oct's previous-day "
               "move is almost exactly 0, so that flag is fragile.", F),
              ("", F), ("Backtest-style (first exchange 1-minute candle from 09:16, open + 1 tick, v12 on 1-minute last prices)", FB),
              (f"   backtest-style mean {bs['backtest-style net %'].mean():+.2f} %; today's book {bk.mean():+.2f} %; live as booked {live_mean:+.2f} % "
               f"(same {len(bs)} trades).", F),
              ("", F), ("5 · Entry rules (signs on exchange minutes; buy at the first today's-book ask with spread ≤ 10 % after the sign; v12 on the bid)", FB),
              (f"   Baseline, the same buy from 09:16: mean {rinfo['base mean']:+.2f} %, ₹{rinfo['base rs']:,.0f}.", F)]
    for lab in NAMED:
        x = nm[f"{lab} · net %"]
        lines.append((f"   {lab}: {int(x.notna().sum())} trades, mean {x.mean():+.2f} %, vs the 09:16 buy on the same trades "
                      f"{nm.loc[x.notna(), '09:16 buy · net %'].mean():+.2f} %", F))
    lines += [(f"   All {rinfo['rules']:,} rules ({rinfo['eligible']:,} with ≥ 10 live trades): Spearman of backtest mean (all days) vs live mean "
               f"{rinfo['spearman all']:+.2f}; with trades relabelled inside each day (timing kept, chart link broken) it averages "
               f"{rinfo['null spearman mean']:+.2f} (95 %: {rinfo['null spearman p95']:+.2f}), p {rinfo['null p']:.3f}. The backtest's top 100 rules made "
               f"{rinfo['top100 backtest -> live mean']:+.2f} % live, its bottom 100 {rinfo['bottom100 backtest -> live mean']:+.2f} %. "
               f"{rinfo['beat 09:16 share']:.0f} % of rules beat the 09:16 buy on the same trades. The rules share about 44 signs and 4 days, "
               "so this is a few independent pieces of evidence, not 10,000.", F),
              ("", F), ("6 · Models trained on the backtest, scored on the live trades (fail = today's-book replay loses)", FB)]
    for _, r in md.iterrows():
        lines.append((f"   {r['model (trained on the 335 backtest trades)']}: AUC {r['AUC on live (0.50 = coin flip)']:.2f}; same-day pairs AUC "
                      f"{r['same-day pairs AUC']:.2f} ({int(r['same-day pairs'])} pairs); {int(r['distinct scores'])} distinct scores", F))
    lines += [("   Nifty's inputs are the same for every trade of a day, so the trade-level AUC mostly sorts the 4 days. Within a day "
               "(the choice the models would actually make) they are close to a coin flip.", F),
              ("", F), ("Research only: nothing live changes. Plan: strategies/S1_fade_live_retest.md.", F)]
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    for i, (txt, font) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=txt)
        c.font = font
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 170
    sheet(wb, "Trades", tr, "The live fade trades (paper-state ledger). Net % = net ₹ / (buy × quantity).")
    sheet(wb, "1 Live vs replay", rep, "v12 and wider stops replayed on the websocket 1-second bid: from the live fill as booked, and from "
          "the first today's-book ask (old-book fills re-made).")
    sheet(wb, "2 Stops", st, "Each exit on the same trades, sold at the best bid.")
    sheet(wb, "3 Max up", mx, "From the today's-book buy, today's book only, to 15:30. Bid = best bid; last = last price. Later sessions: Upstox 1-minute candles.")
    sheet(wb, "4 Market pattern", pd.concat([dm, pd.DataFrame([{}]), pat], ignore_index=True), "Nifty per day (Upstox 1-minute), then the groups.")
    sheet(wb, "Backtest-style", bs, "What the vendor-candle backtest would book for each live trade (Upstox exchange minutes).")
    sheet(wb, "5 Named rules", nm, "The rules picked by the earlier studies, trade by trade: buy time and net %.")
    sheet(wb, "5 All rules", rt.sort_values("backtest rank", na_position="last"),
          "Every rule: live result next to its backtest numbers (rank from S1_fade_pattern_entry_more.xlsx).")
    sheet(wb, "6 Models", pd.concat([md, pd.DataFrame([{}]), probs], ignore_index=True),
          "Models trained on the 335 backtest trades (inputs known at 09:16), scored on the live trades.")
    wb.save(path)
