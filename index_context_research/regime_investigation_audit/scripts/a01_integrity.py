"""Audit A01: dataset integrity of the regime investigation (read-only). Prints facts; no agent code is imported."""
import os, hashlib, json
import pandas as pd, numpy as np
R = "index_context_research/"
RI = R + "regime_investigation/"
I = RI + "interim/"
ctx = pd.read_csv(R + "results/context_dataset.csv")
print("context_dataset rows", len(ctx), ctx.tset.value_counts().to_dict(), "day range", ctx.day.min(), ctx.day.max())
print("duplicates (tset,day):", ctx.duplicated(["tset", "day"]).sum())
print("G1F subset of G1 (same day rows, same net_pct)?")
g1 = ctx[ctx.tset == "G1"].set_index("day"); g1f = ctx[ctx.tset == "G1F"].set_index("day")
print("  G1F days not in G1:", len(set(g1f.index) - set(g1.index)), "| max |net_pct diff|:", float((g1f.net_pct - g1.loc[g1f.index].net_pct).abs().max()))
rep = pd.read_csv("g1_research/results/g1_live_replay_trades.csv")
print("replay file rows", len(rep), "g1f==1:", int((rep.g1f == 1).sum()), "| ctx G1 vs replay net_rs sum", round(ctx[ctx.tset == 'G1'].net_rs.sum()), round(rep.net_rs.sum()),
      "| G1F", round(ctx[ctx.tset == 'G1F'].net_rs.sum()), round(rep[rep.g1f == 1].net_rs.sum()))
print("prospective window rows (day >= 2026-11-13):", int((ctx.day >= "2026-11-13").sum()))
lab = pd.read_csv(I + "agent3_regimes/regime_labels.csv")
print("labels rows", len(lab), lab.strategy.value_counts().to_dict(), "dup (strategy,date):", int(lab.duplicated(["strategy", "date"]).sum()))
m = {"G1-F": "G1F", "G1": "G1", "G1-C": "G1C", "XP": "XP"}
for s, k in m.items():
    a = lab[lab.strategy == s].set_index("date"); b = ctx[ctx.tset == k].set_index("day")
    common = a.index.intersection(b.index)
    print(f"  label vs context [{s}]: n label {len(a)}, n ctx {len(b)}, matched dates {len(common)}, max|net_pct diff| {float((a.loc[common].net_pct - b.loc[common].net_pct).abs().max()):.4f}, max|net_rs diff| {float((a.loc[common].net_rs - b.loc[common].net_rs).abs().max()):.4f}")
print("--- anatomy files vs context (the MAE join)")
for s, f, k in (("G1-F", "anatomy_dataset.csv", "G1F"), ("G1", "anatomy_dataset_G1.csv", "G1"), ("G1-C", "anatomy_dataset_G1C.csv", "G1C")):
    a = pd.read_csv(I + "agent2_anatomy/" + f); b = ctx[ctx.tset == k]
    print(f"  {s}: anatomy rows {len(a)}, tset values {a.tset.unique().tolist()}, dup days {int(a.duplicated('day').sum())}, ctx rows {len(b)}")
    j = a.merge(b[["day", "net_pct", "net_rs"]], on="day", suffixes=("_an", "_ctx"))
    print(f"     matched {len(j)}, max|net_pct diff| {float((j.net_pct_an - j.net_pct_ctx).abs().max()):.4f} (engine re-run values differ slightly), max|net_rs diff| {float((j.net_rs_an - j.net_rs_ctx).abs().max()):.2f}")
    print(f"     missing mae {int(a.mae_any_pct.isna().sum())}, missing mfe {int(a.mfe_any_pct.isna().sum())}")
print("--- gift labels (same-contract)")
g = pd.read_csv(I + "agent3b_gift_regimes/gift_labels_samecontract.csv")
print("rows", len(g), g.strategy.value_counts().to_dict(), "missing gift_ret_samecontract by strategy:", g[g.gift_ret_samecontract.isna()].strategy.value_counts().to_dict())
print("--- external features")
e = pd.read_csv(I + "agent4_external/external_features.csv")
print("rows", len(e), e.strategy.value_counts().to_dict())
print(e.isna().mean().sort_values(ascending=False).head(10).round(2).to_dict())
print("--- hashes: manifest vs files")
man = json.load(open(RI + "DATA_DOWNLOAD_MANIFEST.json"))
bad = 0
for f, v in man["files"].items():
    p = RI + "external_data/" + f
    if not os.path.exists(p):
        print("   missing", f); bad += 1; continue
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    if h != v["sha256_16"]:
        print("   HASH MISMATCH", f); bad += 1
print("manifest files", len(man["files"]), "problems", bad)
