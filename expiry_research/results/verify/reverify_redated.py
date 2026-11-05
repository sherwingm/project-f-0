"""List calendar pointers to an expiry first traded (raw bhavcopy, under that date) after the row date, and tag
whether the expiry is a re-dated one (data/expiry_relabels.csv). Output: results/verify/reverify_redated_rows.csv"""
import sys, os, glob
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
S = os.environ.get("INDEX_STORE", "../fo-index-data/data/index"); R = "expiry_research"
rel = pd.read_csv(f"{R}/data/expiry_relabels.csv", dtype=str)
out = []
for u in ["NIFTY", "BANKNIFTY"]:
    b = pd.concat([pd.read_parquet(f, columns=["TradDt", "XpryDt", "FinInstrmTp"]) for f in sorted(glob.glob(f"{S}/options_daily/{u}/*.parquet"))])
    b = b[b.FinInstrmTp.isin(["IDO", "IDF"])]
    first = b.assign(T=pd.to_datetime(b.TradDt).dt.strftime("%Y-%m-%d"), X=pd.to_datetime(b.XpryDt).dt.strftime("%Y-%m-%d")).groupby("X").T.min()
    s = pd.read_csv(f"{R}/data/sessions_{u}.csv", dtype={"date": str})
    r = rel[rel.underlying == u]
    for col in ["next_expiry", "next_weekly", "next_monthly"]:
        for _, x in s[s[col].notna()].iterrows():
            f = first.get(x[col])
            if isinstance(f, str) and f > x["date"]:
                g = r[r.final_expiry == x[col]]
                out.append(dict(underlying=u, date=x["date"], col=col, points_to=x[col], raw_first_under_that_date=f,
                                redated_from=";".join(g.old_expiry), redated_in_data=";".join(g.old_last_traded),
                                split="discovery" if x["date"] <= "2022-12-31" else ("validation" if x["date"] <= "2024-06-30" else "final")))
o = pd.DataFrame(out); o.to_csv(f"{R}/results/verify/reverify_redated_rows.csv", index=False)
print(len(o), "rows; all re-dated:", (o.redated_from != "").all())
print(o.groupby(["underlying", "points_to", "redated_from", "redated_in_data", "split"]).date.agg(["count", "min", "max"]).to_string())
