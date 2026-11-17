"""Assemble MARKET_REGIME_DRAFT.md = header + findings.md (hand-written) + auto-generated tables. Run after regime_tables.py."""
import os
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
R = pd.read_csv(os.path.join(HERE, "regime_tables.csv"))
T = pd.read_csv(os.path.join(HERE, "regime_tests.csv"))
C = pd.read_csv(os.path.join(HERE, "regime_consistency.csv"))
H = pd.read_csv(os.path.join(HERE, "regime_halfyear.csv"))
L = pd.read_csv(os.path.join(HERE, "regime_labels.csv"), parse_dates=["date"])
TR = pd.read_csv(os.path.join(HERE, "triple_status.csv"))
DTE = pd.read_csv(os.path.join(HERE, "supp_dte.csv"))
STR = ["G1-F", "G1", "G1-C", "XP"]
NAME = {"H1": "H1 direction (ret20 quintiles 1=strongly bearish ... 5=strongly bullish)", "H2": "H2 VIX level", "H3": "H3 VIX direction (5 sessions)",
        "H4": "H4 sudden VIX expansion at signal", "H5": "H5 actual NIFTY opening gap", "H6": "H6 S&P 500 previous session",
        "H7": "H7 direction3 x VIX level", "H8": "H8 direction3 x gap", "H9": "H9 VIX level x gap",
        "R1_ret5": "R1 robustness: ret5 quintiles", "R2_ret10": "R2 robustness: ret10 quintiles", "R3_ma": "R3 robustness: MA structure"}


def f(x, d=1):
    return "-" if x != x else f"{x:.{d}f}"


def tab(sec, hy, st):
    x = R[(R.section == sec) & (R.hypothesis == hy) & (R.strategy == st) & (R.n > 0)]
    lines = ["| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |", "|---|---|---|---|---|---|---|---|---|"]
    for _, r in x.iterrows():
        if r.n < 10:
            lines.append(f"| {r.regime} | {int(r.n)} | too few | too few | | | | | |")
        else:
            lines.append(f"| {r.regime} | {int(r.n)} | {f(r.win_rate,0)} | {f(r.mean_net_pct)} [{f(r.boot_lo,0)}, {f(r.boot_hi,0)}] | {f(r.median_net_pct)} | {r.total_net_rs:,.0f} | {f(r.maxup_mean,0)} | {f(r.maxup_ge100,0)} | {f(r.top5pct_share_of_total_rs,0)} |")
    return "\n".join(lines)


def tests(sec, st):
    x = T[(T.section == sec) & (T.strategy == st) & T.hypothesis.str.startswith("H")]
    lines = ["| hyp | cells with n>=10 | Kruskal-Wallis p | named Welch diff (pp) | Welch p | BH 10% |", "|---|---|---|---|---|---|"]
    for _, r in x.iterrows():
        lines.append(f"| {r.hypothesis} | {int(r.n_cells_ge10)} | {f(r.kw_p,3)} | {(r.welch_pair + ': ' + f(r.welch_diff_pct)) if r.welch_pair == r.welch_pair and r.welch_diff_pct == r.welch_diff_pct else '-'} | {f(r.welch_p,3)} | {'SURVIVES' if r.bh10_survives else 'no'} |")
    return "\n".join(lines)


out = []
out.append(open(os.path.join(HERE, "findings.md"), encoding="utf-8").read())
out.append("\n---\n# Part A. EXPLANATORY (whole sample, 2024-10-01 to 2026-10-23, entries). Descriptive tables\n")
out.append("Units: net % = net rupees after slippage and all charges / rupees of premium paid; Rs = net rupees (separate). CI = bootstrap 95 % of the mean net %, resampling trading days, 5000 draws, seed 20261117. 'top-5 % share' = rupees of the best ceil(5 % n) trades / total rupees (blank = total not positive; above 100 means the rest lost money). maxup = best option price through the next close, % over price paid. Cells n < 10 are shown as 'too few' with no numbers.\n")
for st in STR:
    out.append(f"\n## {st}\n\nTests (whole sample; Kruskal-Wallis on net % across classes with n>=10; Benjamini-Hochberg 10 % over H1-H9 for this strategy):\n\n" + tests("explanatory_all", st) + "\n")
    for hy in NAME:
        out.append(f"\n**{NAME[hy]}**\n\n" + tab("explanatory_all", hy, st) + "\n")
out.append("\n## Cross-strategy: direction3 (collapsed ret20 classes) under the same regimes\n")
for st in STR:
    out.append(f"\n**{st}**\n\n" + tab("explanatory_all", "X1_dir3", st) + "\n")
out.append("\n## Triple (direction3 x VIX level x gap)\n\n| strategy | cells | smallest cell | cells >= 10 | status |\n|---|---|---|---|---|")
for _, r in TR.iterrows():
    out.append(f"| {r.strategy} | {r.cells} | {r.min_cell_n} | {r.cells_ge10} | {r.status} |")
out.append("\n## Supplementary (not in the 9-hypothesis family): days to expiry\n\n| strategy | dte | n | win% | mean net % [95% CI] | total Rs |\n|---|---|---|---|---|---|")
for _, r in DTE[DTE.n > 0].iterrows():
    out.append(f"| {r.strategy} | {r.dte} | {int(r.n)} | {f(r.win_rate,0)} | {f(r.mean_net_pct)} [{f(r.boot_lo,0)}, {f(r.boot_hi,0)}] | {r.total_net_rs:,.0f} |")
out.append("\n---\n# Part B. PREDICTIVE: rules fixed in advance, discovery = entries to 2025-09-30, then consistency in 2025-10-01 to 2026-10-28\n")
out.append("The second half was already seen descriptively (yearly/quarterly tables, one frozen validation): this is a consistency check, not a pristine holdout. Consistency = class mean minus mean of the other trades, same sign in both periods, computed only when the class and the rest both have n >= 10 in that period.\n")
for st in STR:
    out.append(f"\n## {st}\n\nDiscovery tests (BH 10 % over H1-H9):\n\n" + tests("discovery_to_2025-09-30", st) + "\n")
    c = C[(C.strategy == st)]
    out.append("\nClass difference vs the rest of the trades (pp of net %), discovery vs second half:\n\n| hyp | class | n disc | diff disc | n second | diff second | same sign |\n|---|---|---|---|---|---|---|")
    for _, r in c.iterrows():
        out.append(f"| {r.hypothesis} | {r['class']} | {r.n_disc} | {f(r.diff_vs_rest_disc)} | {r.n_second} | {f(r.diff_vs_rest_second)} | {r.same_sign if r.same_sign == r.same_sign else 'not testable'} |")
    h = H[(H.strategy == st) & (H.n >= 10)]
    out.append("\nBy half-year (cells with n >= 10 only):\n\n| half-year | class | n | mean net % in class | mean net % all trades that half-year |\n|---|---|---|---|---|")
    for _, r in h.iterrows():
        out.append(f"| {r.halfyear} | {r['class']} | {r.n} | {f(r.mean_net_pct)} | {f(r.all_mean_net_pct)} |")
out.append("\n---\nFiles: boundaries.json, regime_labels.csv, regime_tables.csv (all sections), regime_tests.csv, regime_consistency.csv, regime_halfyear.csv, triple_status.csv, supp_*.csv, hashes.txt; scripts regimes.py, regime_tables.py, build_draft.py.")
open(os.path.join(HERE, "MARKET_REGIME_DRAFT.md"), "w", encoding="utf-8").write("\n".join(out))
print("ok")
