"""Follow-up max up after each decision time (HOLD_PATTERN_PREREG.md, Amendment 1). Own folder; history only.
For each G1 trade: the put's price at next 09:16 and at the next close, and the highest later minute close after each of
those times through the close of day h = min(days to expiry, 3), as % above that decision-time price (no stop, no exit)."""
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
from index_data import load as L  # noqa: E402
from scanner.s3_buy_maxup import max_up  # noqa: E402
from scanner.s3_engine import chain_between  # noqa: E402


def main():
    d = pd.read_csv(os.path.join(REPO, "data", "results", "S3_G1_datasheet.csv"))
    rows = []
    for r in d.to_dict("records"):
        day, expiry = date.fromisoformat(str(r["Day"])[:10]), date.fromisoformat(str(r["Expiry"])[:10])
        k, dte = float(r["Strike"]), int(r["Days to expiry"])
        after = [x for x in L.trade_days("NIFTY", expiry) if x > day]
        o = {"day": day}
        if after:
            h = min(dte, 3, len(after))
            end = after[h - 1]
            chain = chain_between("NIFTY", expiry, day, end)
            for tag, (dd, hh, mm) in {"d2": (after[0], 9, 16), "d3": (after[0], 15, 29)}.items():
                t_dec = L.at(dd, hh, mm)
                px = L.price_at(chain, k, "PE", t_dec, stale=30)
                o[f"px_{tag}"] = px
                if px and px > 0 and (tag == "d2" or end > after[0]):
                    m = max_up(chain, [("B", k, "PE", px, 0.0)], t_dec, t_dec, L.at(end, 15, 29))
                    o[f"fu_{tag}"] = m["max_up_any_pct"]
        rows.append(o)
    pd.DataFrame(rows).to_csv(os.path.join(ROOT, "data", "g1_followup_trades.csv"), index=False)
    print(pd.DataFrame(rows).describe().round(1).to_string())


if __name__ == "__main__":
    main()
