"""Agent 3b: GIFT overnight / indicated-vs-actual / Asia labels per trade. Read-only on inputs.
Outputs: gift_labels.csv, gift_label_checks.txt, hashes.txt (written by gift_tables.py too)"""
import hashlib, os
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 4))
RI = os.path.join(REPO, "index_context_research", "regime_investigation")
EX = os.path.join(RI, "external_data")
LAB = os.path.join(RI, "interim", "agent3_regimes", "regime_labels.csv")
GIFT = os.path.join(EX, "gift_bhavcopy_futures.csv")
N225 = os.path.join(EX, "yahoo", "N225_1d.csv"); HSI = os.path.join(EX, "yahoo", "HSI_1d.csv")
NIDX = os.path.join(REPO, "data", "eod2", "nifty 50.csv")
CTX = os.path.join(REPO, "index_context_research", "results", "context_dataset.csv")
chk = []

L = pd.read_csv(LAB, parse_dates=["date"])
# ---- GIFT near-month NIFTY ----
g = pd.read_csv(GIFT)
g["d"] = pd.to_datetime(g["trade_date"]); g["c"] = g["contract"].astype(str)
n = g[g["c"].str.match(r"^FUTIDXNIFTY\d{2}-[A-Z]{3}-\d{4}$")].copy()
n["exp"] = pd.to_datetime(n["c"].str[11:], format="%d-%b-%Y")
for c in ("prev_settle", "open", "settlement"):
    n[c] = pd.to_numeric(n[c], errors="coerce")
n_all = len(n)
n = n[n.exp >= n.d].sort_values(["d", "exp"])
chk.append(f"NIFTY futures rows {n_all}; after dropping already-expired {len(n)}")
nm = n.groupby("d").first()                      # earliest expiry not yet expired
chk.append(f"near-month days {len(nm)}, {nm.index.min().date()} to {nm.index.max().date()}; open==0 days {(nm.open==0).sum()}; prev_settle missing {nm.prev_settle.isna().sum()}")
nm["gift_ret"] = (nm.open / nm.prev_settle - 1) * 100            # primary: same contract, GIFT-to-GIFT
# robustness: previous trade date's own near-month settlement (cross-row; differs only on roll days)
nm["prev_row_settle"] = nm.settlement.shift(1)
nm["gift_ret_rob"] = (nm.open / nm.prev_row_settle - 1) * 100
nm.loc[nm.open <= 0, ["gift_ret", "gift_ret_rob"]] = np.nan
chk.append(f"primary vs robustness differ by >0.05 pt on {(abs(nm.gift_ret-nm.gift_ret_rob)>0.05).sum()} days (roll days); corr {nm.gift_ret.corr(nm.gift_ret_rob):.4f}")
chk.append(f"gift_ret percentiles 1/5/50/95/99: {np.nanpercentile(nm.gift_ret,[1,5,50,95,99]).round(3).tolist()}; abs>3% days: {(nm.gift_ret.abs()>3).sum()}")
# ---- Asia opening gaps ----
def asia(path):
    y = pd.read_csv(path)
    y["t"] = pd.to_datetime(y["timestamp_utc"]) + pd.to_timedelta(y["local_offset_s"], unit="s")
    y["d"] = y["t"].dt.normalize()
    y = y.drop_duplicates("d").set_index("d").sort_index()
    y["open"] = pd.to_numeric(y["open"], errors="coerce"); y["close"] = pd.to_numeric(y["close"], errors="coerce")
    y.loc[y.open <= 0, "open"] = np.nan
    return ((y.open / y.close.shift(1) - 1) * 100)
nk, hs = asia(N225), asia(HSI)
chk.append(f"Nikkei gap days {nk.notna().sum()} (abs>5%: {(nk.abs()>5).sum()}); HSI {hs.notna().sum()} (abs>5%: {(hs.abs()>5).sum()})")
# ---- actual gap check ----
nf = pd.read_csv(NIDX, parse_dates=["Date"]).set_index("Date")
ctx = pd.read_csv(CTX); ctx["day"] = pd.to_datetime(ctx["day"])
gc = (nf.Open / nf.Close.shift(1) - 1) * 100
M = L[["strategy", "date", "gap_pct"]].copy()
M["gap_eod"] = M.date.map(gc)
chk.append(f"context gap_pct vs eod Open/prevClose: max abs diff {(M.gap_pct-M.gap_eod).abs().max():.3f} pt, days>0.05pt {( (M.gap_pct-M.gap_eod).abs()>0.05).sum()} (eod2 gap not used; context gap_pct is the actual 09:15 open)")

L["gift_ret"] = L.date.map(nm.gift_ret); L["gift_ret_rob"] = L.date.map(nm.gift_ret_rob)
L["gift_open_missing"] = L.gift_ret.isna()
L["nikkei_gap"] = L.date.map(nk); L["hsi_gap"] = L.date.map(hs)
L["asia_gap"] = L[["nikkei_gap", "hsi_gap"]].mean(axis=1, skipna=True)
L["asia_n_markets"] = L[["nikkei_gap", "hsi_gap"]].notna().sum(axis=1)
def c3(x, hi, lo, names):
    return np.nan if x != x else (names[0] if x >= hi else (names[2] if x <= lo else names[1]))
L["gift_cls"] = L.gift_ret.map(lambda x: c3(x, 0.3, -0.3, ["gap-up", "flat", "gap-down"]))
L["gift_cls_rob"] = L.gift_ret_rob.map(lambda x: c3(x, 0.3, -0.3, ["gap-up", "flat", "gap-down"]))
L["gap_minus_gift"] = L.gap_pct - L.gift_ret
L["gap_minus_gift_rob"] = L.gap_pct - L.gift_ret_rob
L["ivsa_cls"] = L.gap_minus_gift.map(lambda x: c3(x, 0.2, -0.2, ["stronger", "in line", "weaker"]))
L["ivsa_cls_rob"] = L.gap_minus_gift_rob.map(lambda x: c3(x, 0.2, -0.2, ["stronger", "in line", "weaker"]))
L["asia_cls"] = L.asia_gap.map(lambda x: c3(x, 0.3, -0.3, ["up", "flat", "down"]))
# order of classes for names: gift up/flat/down relabelled to stable strings
keep = ["strategy", "date", "side", "dte", "entry", "period", "halfyear", "gift_ret", "gift_cls", "gift_ret_rob", "gift_cls_rob", "gap_pct", "gap_cls",
        "gap_minus_gift", "ivsa_cls", "gap_minus_gift_rob", "ivsa_cls_rob", "nikkei_gap", "hsi_gap", "asia_gap", "asia_n_markets", "asia_cls",
        "dir3", "vix_level", "net_pct", "net_rs", "maxup"]
L[keep].to_csv(os.path.join(HERE, "gift_labels.csv"), index=False)
chk.append(f"label rows {len(L)}; GIFT missing {int(L.gift_open_missing.sum())}; Asia missing {int(L.asia_gap.isna().sum())}; Asia single-market {(L.asia_n_markets==1).sum()}")
for st, s in L.groupby("strategy"):
    chk.append(f"{st}: n={len(s)} gift {s.gift_cls.value_counts().to_dict()} ivsa {s.ivsa_cls.value_counts().to_dict()} asia {s.asia_cls.value_counts().to_dict()}")
open(os.path.join(HERE, "gift_label_checks.txt"), "w").write("\n".join(chk) + "\n")
with open(os.path.join(HERE, "hashes.txt"), "w") as h:
    for p in (LAB, GIFT, N225, HSI, NIDX, CTX, os.path.join(RI, "interim", "agent3_regimes", "boundaries.json")):
        h.write(f"{hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]}  {os.path.relpath(p, REPO)}\n")
print("\n".join(chk))
