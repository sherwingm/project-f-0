"""S1 arms A/B with a NIFTY-above-50-session-average filter on the signal day (numbers only).
Pre-registered: strategies/S1_nifty_regime_filter.md. Selects from the already simulated LIVE-exit trades."""
from __future__ import annotations

import pandas as pd

from .armb_hold_and_nifty import nifty, nifty_ret, stats
from .backtest_s1_v2 import md
from .build import ROOT


def main() -> None:
    tr = pd.read_csv(ROOT / "data/results/S1_armb_hold_and_nifty_trades.csv")
    tr = tr[(tr.variant == "LIVE") & tr.arm.isin(["A", "B"]) & tr.excluded.isna()].copy()
    nf = nifty("2022-01-01", "2026-11-09")
    ma = nf.rolling(50).mean()
    ok = (nf > ma).to_dict()
    tr["pass"] = [ok.get(max([d for d in nf.index if d <= s]), False) for s in tr.signal_date.astype(str)]
    tr["nifty"] = [nifty_ret(nf, str(e), str(x)) for e, x in zip(tr.entry_date, tr.exit_date)]
    rows = []
    for (arm, period), g in tr.groupby(["arm", "period"]):
        for nm, part in (("kept (NIFTY > 50-day avg)", g[g["pass"]]), ("dropped", g[~g["pass"]])):
            s = stats(part)
            s["mean_nifty_window_pct"] = round(part["nifty"].mean(), 2) if len(part) else None
            s["share_of_trades_pct"] = round(len(part) / len(g) * 100)
            rows.append({"arm": arm, "period": period, "set": nm, **s})
    out = pd.DataFrame(rows)
    rep = ("# S1 NIFTY regime filter\n\nNumbers only. Pre-registered: strategies/S1_nifty_regime_filter.md.\n\n" + md(out) + "\n")
    (ROOT / "data/results/S1_nifty_regime_filter.md").write_text(rep, encoding="utf-8")
    print(rep)


if __name__ == "__main__":
    main()
