"""Agent 4: writes EXTERNAL_DRAFT.md from external_tables.csv / external_tests.csv / external_consistency.csv (numbers) plus fixed prose. Run: python -W ignore build_draft.py"""
import os
import numpy as np
import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))
T = pd.read_csv(OUT + "/external_tables.csv"); S = pd.read_csv(OUT + "/external_tests.csv"); C = pd.read_csv(OUT + "/external_consistency.csv")
HY = S.drop_duplicates("hyp").set_index("hyp")["description"].to_dict()
NAME = {"G1F": "G1-F (primary, 154 trades)", "G1": "G1 puts (259)", "G1C": "G1-C calls (235)", "XP": "XP straddle (107)"}


def f(x, d=1):
    return "-" if pd.isna(x) else f"{x:.{d}f}"


def p(x):
    return "n/a" if pd.isna(x) else (f"{x:.3f}" if x >= 0.001 else "<0.001")


def cellline(r):
    if r is None or r.n == 0: return "n=0"
    tag = " TOO FEW" if r.n < 10 else ""
    return f"n={int(r.n)}{tag}, win {f(r.win_rate,0)}%, mean {f(r.mean_pct)}%, median {f(r.median_pct)}%, Rs {r.total_rs:,.0f}"


def get(s, h, an, c):
    x = T[(T.strategy == s) & (T.hyp == h) & (T.analysis == an) & (T.cls == c)]
    return x.iloc[0] if len(x) else None


def hyp_block(s, h):
    out = [f"**{h}. {HY[h]}**"]
    t = S[(S.strategy == s) & (S.hyp == h)].set_index("analysis")
    classes = [c for c in T[(T.strategy == s) & (T.hyp == h) & (T.analysis == 'whole')].cls if (T[(T.strategy == s) & (T.hyp == h) & (T.cls == c) & T.analysis.isin(['whole'])].n.iloc[0] > 0)]
    for c in classes:
        w, d, h2 = get(s, h, "whole", c), get(s, h, "discovery", c), get(s, h, "second_half", c)
        extra = f"; 95% CI of mean {f(w.ci_lo)} to {f(w.ci_hi)}; max up mean {f(w.maxup_mean,0)}%, >=100%: {f(w.share_ge100,0)}% of trades; top-5% trades = {f(w.top5pct_share_of_gross_profit,0)}% of gross profit"
        out.append(f"- {c} - whole: {cellline(w)}{extra}\n  - discovery: {cellline(d)}\n  - second half: {cellline(h2)}")
    out.append(f"- Kruskal-Wallis p (raw): whole {p(t.loc['whole','KW_p'])}, discovery {p(t.loc['discovery','KW_p'])}, second half {p(t.loc['second_half','KW_p'])}. Welch {t.loc['whole','welch_pair']}: whole diff {f(t.loc['whole','welch_diff_mean_pct'])} pts p {p(t.loc['whole','welch_p'])}; discovery diff {f(t.loc['discovery','welch_diff_mean_pct'])} p {p(t.loc['discovery','welch_p'])}; second half diff {f(t.loc['second_half','welch_diff_mean_pct'])} p {p(t.loc['second_half','welch_p'])} (blank = a class under 10 trades). Missing feature: {int(t.loc['whole','n_missing'])} of {int(t.loc['whole','n_total'])} trades.")
    return "\n".join(out)


_c = C[(C.strategy == "G1F") & (C.family == "main")]
NH = int((_c.order_holds_h2_mean.astype(str) == "True").sum()); NR = int((_c.order_holds_h2_mean.astype(str) == "False").sum()); NT = len(_c) - NH - NR
L = []
A = L.append
A("# Institutional, global, breadth and news conditions: draft (agent 4)")
A("Written 17 Nov 2026 from `external_features.csv` / `external_tables.csv` / `external_tests.csv` / `external_consistency.csv` (all in this folder, built by the scripts here). Original recorded trade results only; nothing re-simulated; no prospective-holdout, sealed or VM data touched; no download. Percentages are net rupees (after slippage and charges) divided by the premium paid; rupees are separate. Raw p-values only: the coordinator applies the final Benjamini-Hochberg over the enlarged family.")
A("## 1. Plain-words summary")
A("- **No external condition separates better from worse G1-F trades in a way that survives scrutiny.** Of 19 pre-registered single-condition tests on G1-F (Kruskal-Wallis, whole sample), one has a raw p below 0.05 (USD/INR, p 0.042); about one in twenty would be expected by chance, and the FII/DII cash test (p 0.082) and the participant-OI level test (p 0.103) are also not significant.")
A("- Pattern worth stating but NOT a finding: in G1-F **FII/DII cash, both buying the previous session** had 15 trades with 1 winner (mean -29.4 %) against 44 'diverge' trades (mean +34.3 %); Welch p 0.004 (KW p 0.082). The window is only Dec 2025 to Oct 2026 (September 2026 missing), the data are third-party and verified on one day, the cell is 15 trades, and the sign is the same for G1 (which contains G1-F) so it is not independent evidence. Descriptive only.")
A("- The strongest single-strategy results are for the **secondary** strategies and are explained by time structure: G1-C and the FII futures long-share level (levels cut in 2024-25 move into another range later, so the 'high' class exists only in the discovery half); G1-C and the US VIX spike (23 trades, nominal p 0.006, same direction in both halves, small spike cell).")
A("- Whether the strategies' periods differ because of institutional positioning, Asia, US, breadth or news **cannot be established** from 154 trades with these conditions: cells are small, the second half has already been seen, and level classes drift.")
A("## 2. Data, alignment, publication times")
A("See `availability_table.md` (variable, source, coverage, publication time, alignment). Key points: every predictor is dated before 09:16 IST of the trade day (Asian opens 05:30 / 07:00 IST; US and commodities closed overnight; breadth, sector, FII/DII and participant files are the previous session's, published that evening). Same-day versions are POST-ENTRY and were not used. **The Yahoo daily USD/INR close equals its open on most days and was rejected; the USD/INR variable uses the hourly series, which exists only from 2024-11-18 (13 of 154 G1-F trades missing).** Brent is quality-limited (daily vs hourly disagree by more than 2 % on 27 of 527 days; 3 G1-F trades sit on such days). DXY had 463 weekend rows with no price, dropped.")
A("## 3. Method (all fixed in advance)")
A("Classes and thresholds are exactly Amendment 1 of `PREREG_REGIME.md`; participant-level terciles come from the 248 session days of 2024-10-01 to 2025-09-30 (independent of any trade return); GDELT is the previous UTC day's tone against the median of the 250 earlier days. Per class: n, wins, losses, win rate, mean and median net %, total net Rs, average profit and loss, max up (mean, median, shares >= 50/100/200 %), top-5 % trades' share of gross profit, bootstrap 95 % interval of the mean (trading days resampled, 5000 draws, seed 20261117). Cells with n < 10 are marked TOO FEW and carry no conclusion. Tests: Kruskal-Wallis over classes with n >= 10 and a Welch difference between two named classes (named in advance in `analyse_external.py`). **Explanatory** = whole sample. **Predictive** = rules fixed in advance, discovery entries to 2025-09-30, then consistency in 2025-10-01 to 2026-10-28 (already seen descriptively, so a consistency check and not a pristine holdout) and by half-year (`external_tables.csv`, analyses `hy_*`). Full tables for all four strategies: `external_tables.csv`; tests: `external_tests.csv`; consistency: `external_consistency.csv`; confound check: `context_checks.csv`.")
A("## 4. G1-F results, by hypothesis (primary)")
for h in ["H12", "H13", "X01", "X02", "X03", "X04", "X05", "X06", "H14", "X07", "H15", "X08", "X09", "X10", "X11", "X12", "X13", "X14", "X15"]:
    A(hyp_block("G1F", h))
A("Supplementary (not in the main family): Brent excluding suspect days gives p " + p(S[(S.strategy == 'G1F') & (S.hyp == 'S01') & (S.analysis == 'whole')].KW_p.iloc[0]) + "; FII cash sign alone Welch p " + p(S[(S.strategy == 'G1F') & (S.hyp == 'S02') & (S.analysis == 'whole')].welch_p.iloc[0]) + "; DII cash sign alone cannot be tested (DII was a net buyer on every day with a G1-F trade).")
A("## 5. Explanatory versus predictive, G1-F")
A("- **Explanatory (whole sample).** Raw KW p-values: " + ", ".join(f"{h} {p(S[(S.strategy=='G1F')&(S.hyp==h)&(S.analysis=='whole')].KW_p.iloc[0])}" for h in ["H12", "H13", "H14", "H15", "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "X10", "X11", "X12", "X13", "X14", "X15"]) + ". Only X02 is below 0.05; no multiplicity correction is applied here.")
A("- **Predictive (discovery, then consistency).** In discovery no G1-F hypothesis has a KW p below 0.05 (smallest: USD/INR 0.070, sector 0.178, S&P 500 0.221). The second half keeps the discovery order of best and worst class (by mean) in " + str(NH) + " hypotheses, reverses it in " + str(NR) + " and is 'too few' or not testable in " + str(NT) + " (`external_consistency.csv`, column `order_holds_h2_mean`; the best/worst class is simply the discovery extreme, not a rule that was set in advance). Examples: breadth 'mid' keeps beating 'low' (35.9 % vs 2.6 % in the second half), S&P 'up' keeps beating 'flat' (18.8 % vs 12.1 %), while Asia 'down' (the discovery best) turns to +1.1 % against +40.4 % for 'flat'. Half-year counts are tiny and are in the consistency file.")
A("- **Same direction in discovery and the second half (G1-F), none significant:** breadth 'mid' above 'low'; S&P 500 'up' above 'flat'; USD/INR 'flat' weak (7.8 % and 7.2 %; the only nominal p below 0.05, whole sample); US VIX spike weak (discovery n 3, second half n 10). **Reversed:** Asia down/flat, high breadth (27.2 % discovery, -21.2 % second half), sector leadership. No condition is consistent and large enough to call a finding.")
A("## 6. Secondary strategies (raw p; full cells in the CSV files)")
for s in ["G1", "G1C", "XP"]:
    A(f"**{NAME[s]}**")
    m = S[(S.strategy == s) & (S.family == "main") & (S.analysis == "whole")]
    low = m[(m.KW_p < 0.10) | (m.welch_p < 0.05)]
    for _, r in low.iterrows():
        d = S[(S.strategy == s) & (S.hyp == r.hyp) & (S.analysis == "discovery")].iloc[0]; h2 = S[(S.strategy == s) & (S.hyp == r.hyp) & (S.analysis == "second_half")].iloc[0]
        A(f"- {r.hyp} ({r.description}): KW p whole {p(r.KW_p)}, discovery {p(d.KW_p)}, second half {p(h2.KW_p)}; Welch {r.welch_pair} diff {f(r.welch_diff_mean_pct)} pts (p {p(r.welch_p)}; n {int(r.welch_n_a)} vs {int(r.welch_n_b)}).")
    n05 = m[m.KW_p < 0.05]
    A(f"- {len(n05)} of {int(m.KW_p.notna().sum())} testable KW tests are below 0.05 in the whole sample (expected about {m.KW_p.notna().sum()*0.05:.1f} by chance).")
A("Notes on those: G1 puts, DII level p 0.034 is a time effect (the 'low' DII class exists only in discovery); G1 and G1-F share the both-buying signal (G1-F is a subset of G1); G1-C FII-level p 0.003 is likewise a time effect (the 'high' class has 37 trades, all in discovery, mean -37.5 %, and does not exist in the second half); G1-C VIX-spike: calls +25.9 % on 23 spike trades vs -15.3 % on 191 others, second half +43.2 % (n 12) vs -24.2 %: same direction in both halves, small cell, and the opposite sign to G1-F puts (spike: +0.3 % vs +19.7 %); XP: nothing.")
A("## 7. Confounding checks")
A("`context_checks.csv` gives the mean previous-session NIFTY return of each class (G1-F). Breadth is largely the previous-day market direction (high breadth classes follow +0.48 % NIFTY days, low breadth follows -0.46 % days), so a breadth result is a previous-day direction result. FII/DII both-buying does not follow a particularly up day (+0.07 % vs +0.02 %), so that cell is not explained by the previous day's direction. Sector leadership is unrelated to previous-day direction in size.")
A("## 8. What is impossible or too weak to establish")
A("- FII/DII cash: only 59 G1-F trades have a value, all in Dec 2025 to Oct 2026 (September 2026 missing at source); the data are third party and verified on a single day; 'both selling' never occurs for G1-F (0 trades), so only two classes can be compared.")
A("- Participant-OI level classes drift: with terciles fixed on 2024-10..2025-09, the second half falls almost entirely into one class (e.g. FII option stance 77 of 79 'high'), so level consistency is untestable; changes (signs) are testable.")
A("- Asia pre-entry needs both Nikkei and Hang Seng to be open: 21 G1-F trades are missing. USD/INR needs the hourly series (from 2024-11-18).")
A("- Events: RBI (13), FOMC (16), Budget (2), one US election date; in G1-F the event cells hold 6, 12 and 8 trades whole and under 10 in each half. No other election, CPI, GDP or geopolitical date exists locally and none was invented. GDELT is a global machine score; whether the stored values equal what was visible at 05:30 IST is unknown.")
A("- No hypothesis can say 'the cause' of good and bad periods: with 154 trades and several of the conditions moving together, these tests have little power; absence of significance is not evidence of no effect.")
A("## 9. Files")
A("`external_features.csv` (one row per strategy-trade, all features, class, publication note), `availability_table.md`, `external_tables.csv`, `external_tests.csv`, `external_consistency.csv`, `external_level_cuts.csv`, `context_checks.csv`, `data_checks.txt`, scripts `build_features.py`, `analyse_external.py`, `context_checks.py`, `build_draft.py`, `make_hashes.py`, `hashes.txt`. `superseded_v1/` holds an earlier run that used the older local files and different class definitions; it is not used.")
open(OUT + "/EXTERNAL_DRAFT.md", "w", encoding="utf-8").write("\n\n".join(L) + "\n")
print("ok", sum(len(x) for x in L))
