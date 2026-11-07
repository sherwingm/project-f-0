import sys; sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd, numpy as np
cal = pd.read_csv("expiry_research/data/expiry_calendar.csv", dtype=str)
out = []
for u in ["NIFTY", "BANKNIFTY"]:
    P = pd.read_parquet(f"expiry_research/data/panel_{u}.parquet"); P["date"] = P.date.astype(str)
    days = list(P.date); pos = {d: i for i, d in enumerate(days)}
    ex = cal[(cal.underlying == u) & cal.status.str.startswith("expired")]
    E = sorted(ex.expiry_date); Em = sorted(ex[ex.kind == "monthly"].expiry_date)
    for d in ["2023-03-27", "2023-06-26", "2023-08-31", "2023-09-04", "2024-03-26", "2024-11-12", "2025-08-27", "2025-09-01", "2025-10-17", "2026-03-27"]:
        if d not in pos: continue
        r = P.iloc[pos[d]]
        ne = [e for e in E if e >= d][0]; nm = [e for e in Em if e >= d][0]
        out.append(dict(u=u, date=d, mine_next_exp=ne, mine_sess_to_exp=pos[ne] - pos[d] if ne in pos else None,
                        panel_sess_to_exp=r.cal_sessions_to_expiry, mine_is_exp=d in E, panel_is_exp=r.cal_is_expiry,
                        mine_sess_to_mon=pos[nm] - pos[d] if nm in pos else None, panel_sess_to_mon=r.cal_sessions_to_monthly,
                        opt_near_expiry_listed=r.f_opt_near_expiry, opt_near_dte=r.f_opt_near_dte))
o = pd.DataFrame(out); print(o.to_string()); o.to_csv("expiry_research/results/verify/caltag_checks.csv", index=False)
print([c for c in pd.read_parquet("expiry_research/data/panel_NIFTY.parquet").columns if c.startswith("cal")])
