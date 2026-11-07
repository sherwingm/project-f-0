"""Bias module, stage 2: freeze candidates BEFORE any validation statistic (reports/lld/bias.md).

BH (FDR 10 %) over every discovery test logged by bias_discovery.py. Candidates = discovery reference tests of an
expiry context (tags ctx, dk, xkind, xkind_ctx), n >= 30, q < 0.10. Duplicate row sets (same rows under two tags)
are kept once. They are base-rate facts used as controls, not trading rules.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import re

import numpy as np
import pandas as pd

import bias_common as bc
import stats_utils as su

OUT = bc.OUT
assert not (OUT / "ref_validation.csv").exists(), "validation already computed: freeze must come first"

H = pd.read_csv(OUT / "hypotheses_discovery.csv")
H["q_disc_family"] = su.bh(H["p"].values, 0.10)[0]
H.to_csv(OUT / "hypotheses_discovery.csv", index=False)
print(f"discovery family size {len(H)}; q < 0.10: {(H.q_disc_family < 0.10).sum()}")

R = pd.read_csv(OUT / "ref_discovery.csv")
R = R[R["tag"].isin(["ctx", "dk", "xkind", "xkind_ctx"])]
pat = re.compile(r"^(ctx|dk|xkind|xkind_ctx)=(\S+) (?:mean )?(\S+)")
cand = []
for _, h in H[(H.family == "ref") & (H.q_disc_family < 0.10) & (H.n >= 30)].iterrows():
    m = pat.match(h["test"])
    if not m:
        continue
    tag, lev, tgt = m.groups()
    r = R[(R.ul == h.ul) & (R.tag == tag) & (R.level == lev) & (R.target == tgt)]
    if r.empty:
        continue
    r = r.iloc[0]
    cand.append(dict(ul=h.ul, tag=tag, level=lev, target=tgt, stat=r["stat"], n=int(r["n"]), rate=r["rate"],
                     base=r["base"], effect=r["diff"], p=h.p, q=h.q_disc_family, hyp_id=h["id"]))
C = pd.DataFrame(cand)
TAG_ORDER = {"ctx": 0, "dk": 1, "xkind": 2, "xkind_ctx": 3}
if not C.empty:
    C["o"] = C.tag.map(TAG_ORDER)
    C = C.sort_values(["ul", "target", "o"]).drop_duplicates(["ul", "target", "n", "effect"]).drop(columns="o")
    C = C.sort_values("p").reset_index(drop=True)


def rule_text(tag, lev):
    if tag == "ctx":
        return f"row t where t+1 has exclusive context {lev} (D0 > D+1 > D-k; from cal_next_*)"
    if tag == "dk":
        return f"row t where t+1 is {lev} by cal_next_sessions_to_expiry"
    if tag == "xkind":
        return f"row t where t+1 counts down to a {lev} expiry (cal_next_upcoming_kind)"
    k, c = lev.split("|")
    return f"row t where t+1 counts down to a {k} expiry and has exclusive context {c}"


TDEF = {"gap_up": "y_gap_dir == up", "gap_down": "y_gap_dir == down", "gap_flat": "y_gap_dir == flat",
        "oc_pos": "y_oc > 0", "cc_pos": "y_cc > 0", "big_cc": "|y_cc| >= 1 %", "big_exc": "y_max_exc >= 1 %",
        "y_range_pct": "mean y_range_pct", "y_oc": "mean y_oc", "y_gap_pct": "mean y_gap_pct"}
rows = []
for i, c in C.iterrows():
    rows.append(dict(id=f"BIAS-C{i + 1:02d}", underlying=c.ul, tag=c.tag, level=c.level,
                     rule=rule_text(c.tag, c.level), decision_time="TCLOSE(t) (calendar known in advance)",
                     target=c.target, target_def=TDEF[c.target], stat=c.stat,
                     direction="higher" if c.effect > 0 else "lower", disc_n=c.n, disc_rate=c.rate,
                     disc_base=c.base, disc_effect=c.effect, disc_p=c.p, disc_q=c.q, hyp_id=c.hyp_id,
                     small_n=c.n < 30))
F = pd.DataFrame(rows, columns=["id", "underlying", "tag", "level", "rule", "decision_time", "target", "target_def",
                                "stat", "direction", "disc_n", "disc_rate", "disc_base", "disc_effect", "disc_p",
                                "disc_q", "hyp_id", "small_n"])
F.to_csv(OUT / "candidates_frozen.csv", index=False)
pd.set_option("display.width", 250)
print(F[["id", "underlying", "tag", "level", "target", "direction", "disc_n", "disc_rate", "disc_base",
         "disc_effect", "disc_p", "disc_q"]].to_string(index=False))
with open(OUT / "freeze_stdout.txt", "w", encoding="utf-8") as f:
    f.write(f"discovery family size {len(H)}; q<0.10: {(H.q_disc_family < 0.10).sum()}\n")
    f.write(F.to_string(index=False))
