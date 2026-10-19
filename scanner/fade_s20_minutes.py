"""S1 v10 fade · the -20 % stop on 1-minute prices: when it fires, and how high the option goes AFTER it fired.

    python -m scanner.fade_s20_minutes

Descriptive (the user's question, 2026-10-20: "after the closing of 20% of 71% trade, how much it peaks"). The v10 Rs 2+
trades with day 0 from Oct 2024 (Upstox's minute history starts there) to 2026-09-25: data/results/
S1_v10_bandv10_contracts.csv, minute candles S1_v10_bandv10_minutes.csv (GitHub fetch). Entry = the backtest's (day-0
open + 1 tick); stop = 0.80 x entry; it fires in the first minute whose low <= the stop (the 09:15 minute counts: the
entry is its first trade). After it fires: the highest minute high to 15:19, and the 15:19 close, as % of entry. The
stop's realistic fill = min(stop, that minute's open) - 1 tick (Rs 0.05 before 2025-11-03, Rs 0.01 from it), real
charges, against the backtest's 15:20 exit (e1_net). Writes data/results/S1_v10_s20_minutes.md.
"""
from __future__ import annotations

import pandas as pd

from server import charges as ch

from .backtest_s1_v2 import md
from .build import ROOT
from .stats import clustered_t

RES = ROOT / "data" / "results"
TICK_CHANGE = "2025-11-03"


def one(m: pd.DataFrame, r) -> dict | None:
    m = m[(m["t"] >= "09:15") & (m["t"] <= "15:19")]
    if m.empty:
        return None
    entry, stop = float(r.entry_price), 0.80 * float(r.entry_price)
    tick = 0.05 if r.day0 < TICK_CHANGE else 0.01
    hit = m[m["l"] <= stop + 1e-9]
    out = {"symbol": r.symbol, "day0": r.day0, "side": r.side, "lot": int(r.lot), "entry": entry,
           "close_pct": round((float(m["c"].iloc[-1]) / entry - 1) * 100, 1), "e1_net": float(r.e1_net),
           "day_high_pct": round((float(m["h"].max()) / entry - 1) * 100, 1), "fired": not hit.empty}
    if hit.empty:
        out["s20_net"] = float(r.e1_net)
        return out
    i = hit.index[0]
    row = m.loc[i]
    after = m.loc[i:]                                            # from the stop's minute to 15:19
    later = m.loc[m.index > i]
    fill = max(tick, round(min(stop, float(row["o"])) - tick, 2))
    c = ch.leg(r.side, "BUY", int(r.lot), entry)["total"] + ch.leg(r.side, "SELL", int(r.lot), fill)["total"]
    out.update({"stop_time": row["t"], "fill": fill,
                "peak_after_pct": round((float(later["h"].max()) / entry - 1) * 100, 1) if len(later) else None,
                "peak_after_time": later.loc[later["h"].idxmax(), "t"] if len(later) else None,
                "high_before_stop_pct": round((float(m.loc[:i, "h"].max()) / entry - 1) * 100, 1),
                "s20_net": round((fill - entry) * int(r.lot) - c, 2)})
    return out


def main() -> None:
    c = pd.read_csv(RES / "S1_v10_bandv10_contracts.csv")
    mins = pd.read_csv(RES / "S1_v10_bandv10_minutes.csv")
    mins["t"] = mins["ts"].str[11:16]
    by = {k: g.sort_values("ts").reset_index(drop=True) for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
    rows = [x for r in c.itertuples() if (x := one(by.get((r.symbol, r.day0, r.side, float(r.strike)), pd.DataFrame()), r))]
    t = pd.DataFrame(rows)
    t.to_csv(RES / "S1_v10_s20_minutes_trades.csv", index=False)
    f = t[t["fired"]]
    pa = f["peak_after_pct"].dropna()
    share = lambda s, x: round((s >= x).mean() * 100, 1)                                      # noqa: E731
    peak = pd.DataFrame([{
        "stopped trades": len(f), "of all": f"{len(f)} / {len(t)} ({len(f) / len(t) * 100:.0f} %)",
        "median peak after stop": f"{pa.median():+.1f} %", "back to entry (>= 0 %)": f"{share(pa, 0)} %",
        ">= +20 %": f"{share(pa, 20)} %", ">= +50 %": f"{share(pa, 50)} %", ">= +100 %": f"{share(pa, 100)} %",
        "closed (15:19) above entry": f"{share(f['close_pct'], 0.0001)} %",
        "median 15:19 close": f"{f['close_pct'].median():+.1f} %"}]).T.reset_index()
    peak.columns = ["stopped trades, after the stop fired", "value"]
    when = f["stop_time"].map(lambda x: "09:15" if x == "09:15" else "09:16-09:30" if x <= "09:30" else
                              "09:31-11:00" if x <= "11:00" else "11:01-15:19").value_counts().reindex(
        ["09:15", "09:16-09:30", "09:31-11:00", "11:01-15:19"]).fillna(0).astype(int)
    bands = pd.cut(pa, [-101, -50, -20, 0, 20, 50, 100, 10_000],
                   labels=["< -50 %", "-50..-20 %", "-20..0 %", "0..+20 %", "+20..+50 %", "+50..+100 %", ">= +100 %"])
    dist = bands.value_counts().reindex(bands.cat.categories).rename("trades").reset_index()
    dist.columns = ["peak after the stop (vs entry)", "trades"]
    money = pd.DataFrame([
        {"exit": "15:20 (backtest e1_net)", "total_rs": round(t["e1_net"].sum()), "wins": int((t["e1_net"] > 0).sum()),
         "t": clustered_t(t["e1_net"] / (t["entry"] * t["lot"]) * 100, t["day0"])},
        {"exit": "-20 % stop on minutes, real fill", "total_rs": round(t["s20_net"].sum()), "wins": int((t["s20_net"] > 0).sum()),
         "t": clustered_t(t["s20_net"] / (t["entry"] * t["lot"]) * 100, t["day0"])},
        {"exit": "  of which the stopped trades: 15:20", "total_rs": round(f["e1_net"].sum()), "wins": int((f["e1_net"] > 0).sum()), "t": None},
        {"exit": "  of which the stopped trades: stop", "total_rs": round(f["s20_net"].sum()), "wins": int((f["s20_net"] > 0).sum()), "t": None}])
    text = "\n".join([
        "# S1 v10 fade · the -20 % stop on 1-minute prices: what the option did after the stop fired\n",
        f"Descriptive. {len(t)} v10 Rs 2+ trades with day-0 minute candles, Oct 2024 - Sep 2026 (Upstox's minute history "
        "starts Oct 2024). Entry = day-0 open + 1 tick (the backtest's); stop 0.80 x entry, fired in the first minute whose "
        "low <= the stop. Peaks are the highest minute high after the stop's minute, to 15:19, as % of entry.\n",
        "## After the stop fired\n\n" + md(peak),
        "## Peak after the stop, distribution\n\n" + md(dist),
        "## When the stop fired\n\n" + md(when.rename("trades").reset_index().rename(columns={"index": "minute", "stop_time": "minute"})),
        "## Money: the stop with a real fill vs the 15:20 exit\n\n" + md(money)
        + "\n\nThe stop's fill = min(stop, that minute's open) - 1 tick: a market sell, not the stop level (the daily-data "
          "study filled at the level). Trades: data/results/S1_v10_s20_minutes_trades.csv.\n",
    ])
    (RES / "S1_v10_s20_minutes.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
