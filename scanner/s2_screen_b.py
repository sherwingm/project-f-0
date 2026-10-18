"""S2 screen B runner (strategies/S2_put_screens_B.md + addendum 2026-10-18). Stock-level screens, short direction.

    EVENTS_DB=<seeded store> python -m scanner.s2_screen_b --recount   # gate 4: event counts only, no returns
    EVENTS_DB=<seeded store> python -m scanner.s2_screen_b             # all screens -> data/results/S2_screen_B.md / .xlsx

§1 parent indicators, §2 market backdrop, §3 sector rotation, §4 gap fill, §5 weak results, §6 order-book hype (proxy).
§7 QIP is the unchanged `python -m scanner.event_screens --only qip`.
"""
from __future__ import annotations

import argparse
import json
import logging
import math

import numpy as np
import pandas as pd

from . import s2b_common as C
from .build import ROOT

log = logging.getLogger("s2_screen_b")
RES = ROOT / "data" / "results"


def store_events() -> list[dict]:
    from .events.store import Store
    with Store() as st:
        return [e for t in ("results", "results_date", "order_win") for e in st.all_of_type(t)]


def counts(ev: pd.DataFrame, label: str, unit_dates: bool = False) -> dict:
    if ev is None or ev.empty:
        return {"cell": label, "N": 0, "dates": 0}
    by_year = ev["date"].str[:4].value_counts().sort_index().to_dict() if not unit_dates else \
        ev.drop_duplicates("date")["date"].str[:4].value_counts().sort_index().to_dict()
    return {"cell": label, "N": len(ev), "dates": int(ev["date"].nunique()), **{f"{y}": by_year.get(y, 0) for y in C.YEARS}}


def recount(m: C.Market, evs: list[dict], fin: dict) -> pd.DataFrame:
    from . import gap_screen as G
    from . import s2_market_filter as F
    from . import s2_order_screen as O
    from . import s2_parent_screen as Pp
    from . import s2_rotation_screen as R
    from . import s2_weak_results_screen as W
    rows = []
    pe = Pp.events(m)
    pe = pe[~pe["group"].isin(Pp.SIDE_ONLY)]
    for k, name in ((1, "§1 P1 k=1 (shock dates)"), (5, "§1 P2 k=5 (shock dates)")):
        rows.append(counts(pe[pe["k"] == k], name, unit_dates=True))
    base = F.base_events(m)
    st = F.states(m, base)
    rows.append(counts(base, "§2 F0 base"))
    for f in ("F1 BRENT_UP5", "F2 US_OVERNIGHT_DOWN", "F3 NIFTY_DOWNTREND"):
        rows.append(counts(base[st[f] == True], f"§2 {f} (on)"))           # noqa: E712
    rows.append(counts(R.events(m), "§3 R1/R2 rotation"))
    gev = G.events(m, G.results_days(m, evs))
    for name, (x, s) in G.CELLS.items():
        if not name.startswith("G5"):
            rows.append(counts(G.cell_events(gev, x, s), f"§4 {name}"))
    wev, drops = W.events(m, evs, fin)
    rows.append(counts(wev[wev["pre5"] >= 0], "§5 W1 weak, pre5 >= 0") | {"drops": json.dumps(drops)})
    oev = O.events(m, evs)
    for name, rule in O.CELL_RULES.items():
        if name.startswith("O"):
            rows.append(counts(O.cooldown(oev[rule(oev)]), f"§6 {name}"))
    return pd.DataFrame(rows)


def run(m: C.Market, evs: list[dict], fin: dict) -> tuple[list[dict], dict]:
    from . import gap_screen as G
    from . import s2_market_filter as F
    from . import s2_order_screen as O
    from . import s2_parent_screen as Pp
    from . import s2_rotation_screen as R
    from . import s2_weak_results_screen as W
    out, info = [], {}
    log.info("§1 parents"); r, i = Pp.cells(m); out += r; info["§1"] = i
    log.info("§2 market backdrop"); r, i = F.cells(m); out += r; info["§2"] = i
    log.info("§3 rotation"); r, i = R.cells(m); out += r; info["§3"] = i
    log.info("§4 gap fill")
    gev = G.add_returns(m, G.events(m, G.results_days(m, evs))); out += G.cells(gev); info["§4"] = {"events (G >= 2 %)": len(gev)}
    log.info("§5 weak results")
    wev, drops = W.events(m, evs, fin); wev = W.add_returns(m, wev); out += W.cells(wev); info["§5"] = {"weak events": len(wev), "drops": drops}
    log.info("§6 order-book hype")
    oev = O.add_returns(m, O.events(m, evs)); out += O.cells(oev); info["§6"] = {"order-win events": len(oev)}
    return out, info


def write(rows: list[dict], info: dict, rc: pd.DataFrame | None) -> None:
    import xlsxwriter
    from .backtest_s1_v2 import md
    df = pd.DataFrame(rows)
    front = ["screen", "cell", "h", "role", "PASS", "failed", "unit", "N", "G", "mean", "median", "hit %",
             "t (min of date / week)", "t date", "years positive", "mean needed for t=3"]
    df = df[[c for c in front if c in df.columns] + [c for c in df.columns if c not in front]]
    df.to_csv(RES / "S2_screen_B_cells.csv", index=False)
    tests = df[df["role"] == "pass test"]
    passed = tests[tests["PASS"] == "PASS"]
    key = ["screen", "cell", "h", "PASS", "failed", "N", "G", "mean", "median", "hit %", "t (min of date / week)",
           "years positive"] + [f"{y} mean" for y in C.YEARS]
    head = ("Stock-level screens, short direction (not trades). strategies/S2_put_screens_B.md + addendum 2026-10-18. "
            "Pass: N >= 100 and >= 60 dates, t >= 3 (smaller of date / week clustered), mean >= +0.6 %, positive in >= 5 of "
            "6 years incl. 2025 and 2026 (§6: 4 of 5, 2022-26), robust without the 5 biggest dates, the largest stock, "
            "and the S2 step-1 signals. Because S2 step 2 failed, a pass needs a mean >= +1.0 % to get a put backtest.")
    text = ["# S2 screen B · results\n", head + "\n",
            f"Pass tests: {len(tests)} rows; passing: {len(passed)}.\n",
            "## Pass tests\n", md(tests[[c for c in key if c in tests.columns]]),
            "## Run notes\n", "```\n" + json.dumps(info, indent=1, default=str) + "\n```\n"]
    if rc is not None:
        text += ["## Gate 4 recount (events, no returns)\n", md(rc)]
    text += ["## Every row (pass tests and descriptive)\n", md(df[[c for c in key + ["role"] if c in df.columns]])]
    (RES / "S2_screen_B.md").write_text("\n".join(text), encoding="utf-8")
    wb = xlsxwriter.Workbook(RES / "S2_screen_B.xlsx")
    F = lambda **k: wb.add_format({"font_name": "Arial", "font_size": 10, **k})          # noqa: E731
    H = F(bold=True, font_color="#FFFFFF", bg_color="#1F3864", text_wrap=True, valign="vcenter", border=1)
    yes, num = F(bold=True, bg_color="#E2F0E4"), F(num_format="0.000;[Red]-0.000")
    for name, d in (("Pass tests", tests[[c for c in key if c in tests.columns]]), ("All rows", df),
                    ("Recount", rc if rc is not None else pd.DataFrame())):
        ws = wb.add_worksheet(name)
        ws.write(0, 0, head, F(italic=True, font_size=9))
        ws.set_row(2, 40)
        for c, h in enumerate(d.columns):
            ws.write(2, c, str(h), H)
            ws.set_column(c, c, 22 if c < 2 else 11)
        for r, row in enumerate(d.itertuples(index=False), 3):
            for c, v in enumerate(row):
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    ws.write_blank(r, c, None)
                elif isinstance(v, (bool, np.bool_)):
                    ws.write(r, c, "yes" if v else "no", F())
                elif isinstance(v, (int, float, np.integer, np.floating)):
                    ws.write_number(r, c, float(v), num)
                else:
                    ws.write(r, c, str(v), yes if v == "PASS" else F())
        ws.freeze_panes(3, 2)
    wb.close()
    print("\n".join(text[:5]))


def main() -> None:
    ap = argparse.ArgumentParser(description="S2 screen B (stock-level, short)")
    ap.add_argument("--recount", action="store_true", help="gate 4: event counts only, no returns")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from .financials import load as load_fin
    m, evs, fin = C.load_market(), store_events(), load_fin()
    log.info("market: %d sessions, %d stocks with prices, %d without eod2", len(m.cal), len(m.c), len(m.dropped_no_eod2))
    rc = recount(m, evs, fin)
    RES.mkdir(parents=True, exist_ok=True)
    rc.to_csv(RES / "S2_screen_B_recount.csv", index=False)
    if a.recount:
        from .backtest_s1_v2 import md
        print(md(rc))
        return
    rows, info = run(m, evs, fin)
    write(rows, info, rc)


if __name__ == "__main__":
    main()
