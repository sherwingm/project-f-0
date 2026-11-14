# Retrospective amendments A5-A8 to stress_audit/PREREG.md (recorded 13 Nov 2026, after the audit and the review)

These are written AFTER the results existed. They document what happened; they do not authorise it and they change no number. `stress_audit/AMENDMENTS.md` (A1-A4, committed before the first
result in f81de746e) is untouched.

**A5 - join fan-out error in the first S1 scenario run (about 17:51:5x IST, 13 Nov).** The first run of `s1_stress.py` after commit f81de746e merged scenario results with the regime table on
(symbol, day0, side). 26 trades share that key with another trade (different strikes or contract sets), so the merge duplicated rows: the baseline showed 365 trades and +2.70 % instead of 339 and +2.861 %, and the
order-ordering bracket showed 417 rows. The error was noticed from the trade count, fixed at about 17:52:43 by carrying a unique trade id (`tid`) through every table, and the script was rerun.
The first run's output was overwritten, was never committed and was never reported; it is known only from the session transcript. The corrected code first appears in commit 3fa031ee3 (diff of s1_stress.py against f81de746e).
Final outputs were checked for duplicates by the independent review (0 duplicate (scenario, tid) rows; regime families sum to 339 / 259 / 154).

**A6 - C7 volatile-day adversity implemented differently from the pre-registration.** PREREG section 3, C7: "on the top decile of days by |NIFTY close-to-close return| (computed on the audit window)".
Implemented: the decile of each trade's own-day |NIFTY return| over the **trade rows** (`stress_audit/common.py add_regimes`), so busy days weigh more. Review figures: the implemented cut flags 10.9 % of S1 trades; the registered
(session-based) wording would flag 5.6 %; S1 C7 mean +2.305 % as run against +2.679 % with the session-based cut. For G1/G1-F the same implementation was used; the registered definition's effect there was not computed.
Decision: C7 stays reported as run and is classified as a **pre-registration deviation, not a fully validated stress result**. For S1 the as-run value was reproduced and the registered-definition value was computed in the review (informational). For G1 and G1-F the as-run value was reproduced through the original engine but **the registered definition's effect was not calculated and is UNVERIFIED**. The same-day return makes it an ex-post stress label, not a trading rule (as in the original wording).

**A7 - G1 trade-audit size.** PREREG section 8 states "G1, 20 trades". Its own categories (3 largest wins, 3 largest losses, 4 stops, 4 next-close exits, 3 ambiguous, 3 gap-through, 3 largest friction) add up to 23, so the
workbook contains 23 G1 trades (30 S1 trades as written). This was disclosed only in STRESS_REPORT.md section 14 and the final message, not as an amendment. Selection is deterministic (seed 20261113) and reproduced identically
by the review's offline rerun.

**A8 - provenance code and report-builder changes made after the first results.** (a) `common.write_manifest` was changed to merge with the earlier manifest and to add a `scripts_clean_at_run` flag (the flag is false in the
final manifest only because of an unrelated untracked file, `server/autoupdate.py`). (b) The bound lines S0W/S0B were labelled "bound only - not used for a verdict" (covered by A1). (c) `build_report.py` text was edited at about
18:12:20 IST, after the manifest (18:10:16, commit 3fa031ee3); the committed report was built by the version committed in 136d3de6f; the difference is one sentence in section 6. (d) `g1_stress.py`, `trade_audit.py`,
`holdout_track.py` and `build_report.py` were first committed (3fa031ee3, 18:06:23) after their first results existed; the pre-registration defined the G1 scenarios in words but did not require scripts to be committed first.
The manifest's missing data hashes are supplied by `MANIFEST_SUPPLEMENT.json`.
