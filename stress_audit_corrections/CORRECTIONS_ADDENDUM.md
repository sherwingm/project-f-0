# Addendum to the stress audit (original: commit 136d3de6f) - corrections of record

**Status: prepared for your approval; nothing here is committed until you approve.** This addendum does not replace, edit or delete any file of the original audit
(`stress_audit/`) or of the independent review (`stress_audit_review/`). Original text is quoted below, never removed. Where an original statement and this addendum
differ, this addendum is the correction of record. Every number comes from an existing output (the audit's CSVs or the review's CSVs); **no new experiment was run**.
SHA-256 of every original audit file is in `MANIFEST_SUPPLEMENT.json` so the originals can be shown to be untouched. The six corrections you approved are 1-6 below;
section 7 lists other statements of the original that this addendum corrects; section 8 lists what is deliberately not corrected.

## 1. S1 first-candle stop uncertainty and the +1.8 % to +3.9 % range (correction 1)
**Why.** The S1 baseline (and every audit scenario built on it) never tests the -20 % stop, or the +10 % trail trigger, inside the entry candle itself. In the 339 trades,
the entry candle's low is at or below the stop level in 47 and its high at or above the +10 % trigger in 115. The original report counted these (section 0 item 3, section 2 row V10, section 11 item 3) but did not quantify them.

| Line | Trades changed | Mean net per trade | Net Rs | t (date-clustered) |
|---|---|---|---|---|
| Original baseline (entry candle not stop-tested) | 0 | +2.861 % | Rs 68,160 | 1.79 |
| 41 unambiguous first-candle stops re-booked (low at or below the stop level, no +10 % print in that candle) | 41 | +2.585 % | Rs 63,474 | 1.60 |
| All 47 re-tested, the 6 candles that also reach +10 % booked STOP-first (lower end of the range) | 47 | +1.786 % | Rs 48,624 | 1.10 |
| All 47 re-tested, the 6 candles that also reach +10 % booked HIGH-first (upper end of the range) | 47 | +3.876 % | Rs 83,039 | 2.63 |

**Reading.** Entry is at the candle's open, so the low can only come after it; the 41 candles that dip to the stop level without a +10 % print are unambiguous stops
that the baseline books as if the stop did not exist in that minute (mean +2.58 % instead of +2.86 %). For the 6 candles that touch both levels the
order inside the minute cannot be known from 1-minute data: stop-first gives +1.79 %, high-first gives +3.88 %. **So the S1 baseline's first-candle
uncertainty is a range of +1.79 % to +3.88 % (about +1.8 % to +3.9 %), and the original +2.86 % lies inside it.** The two end-lines are bounds chosen by
outcome for six trades; they are not estimates and are not used for a verdict.

**Corrected statement to be read with the original.** "S1 fade v12 baseline: +2.86 % a trade, 339 trades, t 1.79, 95 % interval -0.35 to +5.92 %,
first-candle uncertainty +1.786 % to +3.876 % (t 1.10 to 2.63). Insufficient evidence." The conclusion is unchanged; the t of 2.63 at the upper end rests on six
unknowable orderings and is not evidence of an edge.
**Original places this qualifies:** STRESS_REPORT.md section 0 items 2-5, section 3 row B0, section 10 (S1 column), section 11 item 3, section 13 item 3.

**Precision of the range (reconciliation).** The same two numbers appear at three precisions in the record. The **precise values are the 3-decimal ones in `s1_first_candle_range.csv`**
(taken from `stress_audit_review/results/v1_s1_checks.csv`); the others are roundings of them:
| End of the range | Precise value (use this) | 2 decimals (this addendum's text) | 1 decimal (earlier wording) |
|---|---|---|---|
| lower end, stop-first | **+1.786 %** (Rs 48,624, t 1.10) | +1.79 % | +1.8 % |
| upper end, high-first | **+3.876 %** (Rs 83,039, t 2.63) | +3.88 % | +3.9 % |
The earlier "+1.8 % to +3.9 %" (review report M1 and its corrections list, and the correction list you approved) and the "+1.79 % to +3.88 %" in this addendum are the same range; where they are quoted together,
**read the precise values +1.786 % to +3.876 %**. No figure changed; only the number of decimals differs. The review report is not edited.

## 2. G1-F robustness wording (correction 2)
**Original text** (STRESS_REPORT.md, section 0 item 7): "positive in all 27 neighbouring settings and under every stress (combined +16.8 %), but its three filters were chosen on this same history, so this is in-sample."
**Original text** (section 10, robustness row): "**strong** (...), but in-sample."
**Corrected wording.** The 27 settings in `sensitivity_g1.csv` change only the stop (40/50/60 %), the exit time (same-day / next 09:16 / next 15:29) and the strike (one out / ATM / one in) on the
**same 154 trades**; they do not vary the three G1-F filters (gap 0.3 %, width 0.5-0.8 %, VIX 17), and the settings are not independent of each other. The review also moved the filter thresholds
(`stress_audit_review/results/v2_g1f_filter_threshold_map.csv`, informational, 27 cells, none ranked): 27 of 27 re-filtered cells stay above G1's +5.5 %
(range 9.5 % to 25.4 %, 106 to 191 trades), again on the same 259 signals. **Both are sensitivity analyses on the data the filters were fitted to. They show that the
result is not knife-edge in those parameters; they do not validate G1-F.** The strategy page records that the three buckets were picked from nine tables on the same data and that picking on year 1 and applying to
year 2 lifted year 2 only from +4.3 % to +7.0 % on the rupees paid (page figure, **not reproduced** by the audit or the review). The only independent evidence would be trades entered after the freeze
(13 Nov 2026 17:48:58 IST); there are none yet. The label "strong" in the original table is replaced by "held up in every stress line (in-sample)".
**Standard wording of record:** **G1-F - statistical conclusion: in-sample; insufficient evidence for future performance. Held up in every stress line (per-trade % and rupees above zero in all 12), which is a sensitivity result on the same trades, not independent validation.**

## 3. One G1 verdict wording throughout (correction 3)
The original uses two phrasings: "insufficient evidence, **weak under stress**" (section 0 item 6) and "**moderate, split**" (section 10 table). They are reconciled as follows (the facts behind both are right: G1's per-trade %
stays positive in every required stress line while its net rupees are -Rs 3,102 under C1, -Rs 11,194 under C6, -Rs 25,274 under E3 and -Rs 1,449 under C8).
**Wording of record (use this everywhere):**
- **G1 (all breakouts) - statistical conclusion: insufficient evidence. Robustness to the pre-registered execution-stress set: split** - per-trade return % stays above zero in every stress line, but net rupees are at or below zero in C1, C6, E3 and C8.
- **G1-F - statistical conclusion: in-sample; insufficient evidence for future performance. Held up in every stress line (per-trade % and rupees above zero in all 12), which is a sensitivity result on the same trades, not independent validation.**
- **S1 fade v12 - statistical conclusion: insufficient evidence. Robustness to the stress set: weak** (per-trade expectancy below zero in 8 of 15 stress lines); the baseline +2.86 % carries first-candle uncertainty, range +1.786 % to +3.876 % (precise values; +1.79 % to +3.88 % at 2 decimals, about +1.8 % to +3.9 % at 1).

**Where the original wording appears and what it is read as** (originals are untouched; the generator `stress_audit/build_report.py` was not edited, so these strings stay in the committed file):
| File and line | Original | Read as |
|---|---|---|
| `stress_audit/results/STRESS_REPORT.md` line 13 (section 0 item 6) | "insufficient evidence, weak under stress" | G1 standard wording above |
| same, line 14 (item 7) | "positive in all 27 neighbouring settings and under every stress" | section 2 above |
| same, line 17 (item 10) | "Statistical robustness: insufficient (S1, G1), in-sample (G1-F)" | consistent with the standard wording; no change |
| same, line 147 (section 10 table, robustness row) | "moderate, split" (G1), "strong" (G1-F) | G1 "split" as above; G1-F "held up in every stress line (in-sample)" |
| `stress_audit/build_report.py` lines 100, 101, 177 | the generator strings for the same text | same readings; generator not changed |
| `stress_audit_review/REVIEW_REPORT.md` M2 and M10 | already note the inconsistency and the "strong" overreach | resolved by this section |
Other documents (`PROGRESS.md`, `docs/research/experiments.csv`) say "insufficient evidence for all three" and are consistent; they are not edited.

## 4. The C7 deviation from the pre-registration (correction 4) - details in AMENDMENTS_A5_A8.md, A6
**Status label: C7 = PRE-REGISTRATION DEVIATION. It is not a fully validated stress result for any strategy.**
PREREG section 3 defines C7 as extra slippage "on the top decile of days by |NIFTY close-to-close return| (computed on the audit window)". The code computes the decile over the **trade rows**
(each trade's day, so days with many trades count many times), not over all sessions. The label also uses the same-day move, an ex-post stress label, not a tradable rule.
| Strategy | C7 as run | Reproduced by the review | Registered definition's result | Classification |
|---|---|---|---|---|
| S1 fade v12 | +2.305 % (cut 1.14 % (flags 10.9 % of trades) vs session-based cut 1.32 % (would flag 5.6 % of trades)) | yes, by independent code, under the implemented definition | +2.679 % (computed in the review as information only, not in the original audit) | **Deviation**; as-run value verified arithmetically; registered-definition value informational |
| G1 | Rs 34,581 (cut 1.349 % over the G1 trade rows) | yes, through the original engine, under the implemented definition | **not calculated** | **Deviation; effect of the registered definition UNVERIFIED** |
| G1-F | Rs 245,068 | yes, same method | **not calculated** | **Deviation; effect of the registered definition UNVERIFIED** |
C7 stays reported as run but is **not** to be cited as a validated stress result; it is labelled "pre-registration deviation (A6); G1 and G1-F effect unverified". The conclusions in sections 2 and 3 do not depend on it:
without C7, G1's per-trade % is still above zero in the other 11 stress lines and its net rupees are still at or below zero in C1, C6, E3 and C8; G1-F is still above zero in the other 11; S1's count of lines below zero is 8 of 14.
**Evidence grade of the G1 / G1-F stress lines, stated so nothing is read as fully validated:** reproduced through the original engine: C1, C2, C3, C4, C5, C6, E1, E2, E3, E4; reproduced as run but a deviation: C7;
**no independent oracle** (rest on the audit's own simulator, which equals the engine wherever the engine can be used): S5, S6, C8.

## 5. Manifest data provenance and hashing coverage (correction 5), with the coverage evidence and its limits
The original `RUN_MANIFEST.json` hashed 13 S1 input files only. `MANIFEST_SUPPLEMENT.json` comes from a full rerun of the committed pipeline (S1, G1, trade audit, report) with every network socket blocked, writing to a temporary folder that was
deleted. **How reads were captured (three mechanisms):** Python audit hook on open() and on directory-listing events; wrappers logging the path of every call to: pandas.read_parquet, pandas.read_feather, pandas.read_csv, pandas.read_excel, pandas.read_json, pyarrow.memory_map, pyarrow.parquet.read_table, pyarrow.parquet.read_pandas, pyarrow.feather.read_feather, pyarrow.feather.read_table, index_data.load.read_store, scanner.fastio.read_table; sys.modules for repo code that ran; comparison against an expected-file list derived from the loader's own path rules (below).
**What it records:** SHA-256 of **1154 data files read** (1,285 MB: 431 NIFTY option minute files, spot and VIX files, daily files, the S1 contract and minute files, the replay file, the datasheet, the ledger snapshot, bhavcopy caches), of **45 repo code files that actually ran**
(taken from `sys.modules`; the first draft of this supplement listed only 14 because compiled-module caching hides source opens, and it also lacked the native-reader wrappers: both gaps were found by the author on checking and replaced before this addendum), and of **27 files of the original audit** as committed.
fo-index-data checkout 62a232575, clean: True. Repo HEAD when traced: 939f7eef3 (it already includes another session's later documentation commit; no file the pipeline reads was changed by it).
Committed outputs reproduced by the rerun: scenario_results_s1.csv, scenario_results_g1.csv, sensitivity_s1.csv, sensitivity_g1.csv, regimes_s1.csv, regimes_g1.csv, trades_s1_all_scenarios.csv, trades_g1_all_scenarios.csv, s1_ambiguous_trades.csv, g1_ambiguous_trades.csv, TRADE_AUDIT.xlsx (all sheets, cell by cell) (all identical).
Versions: {'python': '3.13.2', 'pandas': '2.3.3', 'numpy': '2.5.2', 'pyarrow': '26.0.0', 'openpyxl': '3.1.5'}. It does not retro-fit the original manifest (its `git_head` stays 3fa031ee3 and `scripts_clean_at_run` stays false because of an unrelated untracked file).

**Does the tracing capture Parquet and the other data files? Evidence, not assertion.** Parquet is read by native code, so the open() hook cannot see it; the loader entry points (`index_data.load.read_store`, `pandas.read_parquet`, `pyarrow.parquet.read_table`, `pyarrow.memory_map`,
`fastio.read_table`, `pandas.read_feather`) were wrapped to log the path they are handed. The result was then **tested against an independent expectation derived from the loader's own path rules**:
| Check | Result |
|---|---|
| NIFTY option files the G1 trades should read (every trading day from each signal day to its exit day, for that expiry) | expected 431; **not found in the hashed list: 0** [] |
| option files actually read | 431 (a surplus over the expected list would be files read by other code paths; not an error) |
| S1 inputs (10 contract/minute files, `S1_v10_trades.csv`, NIFTY daily) | expected 12; **not hashed: 0** [] |
| VIX parquet and the stored replay file | not hashed: 0 [] |
| paths logged by the native-reader wrappers | 1152; not regular files: 0 |
| files seen ONLY by the native wrappers (the open() hook alone would have missed them) | 562 |
| files seen only by the open() hook | 11 |
| files seen by both mechanisms | 581 |
| directories listed or globbed during the rerun | 218 (110 under fo-index-data, 6 under the repo) |
**Limitations (not claimed away):**
1. stat()/exists()/metadata-only calls are not logged by any mechanism available here; a file only stat-ed (not read) is not listed. Python has no audit event for os.stat.
2. Native (C/C++) file reads are captured only through the wrapped entry points listed in `methods`; a read through an unwrapped entry point (for example pyarrow.parquet.ParquetFile or pyarrow.dataset, or a library that opens files itself) would not be logged. None of those entry points is used by the repo code that ran (checked by reading the loader and fastio code), but this is a code-reading argument, not a log.
3. The coverage check compares the log with what the loader's path rules say it should read for the G1 option files and with the known S1 inputs; for the 500+ bhavcopy cache files and other data/cache files completeness rests on the open() hook alone.
4. Feather copies under data/cache/index/feather and data/results/*.feather are derived caches of the Parquet / CSV masters and are listed as data files when Python opened them; the masters are hashed through the loader wrappers.
5. Interpreter, standard-library and site-packages files are not hashed; versions are recorded instead.
6. Subprocesses (git rev-parse / git status in common.py) read .git, which is excluded.
7. The claim covers this rerun on 13 Nov 2026 at the repo HEAD above. It does not prove what the original 18:06-18:12 run read; it shows the committed pipeline reproduces the committed outputs and reads the files listed.
**Static scan of the 45 code files that ran (to support limitation 2 and the network statement):** files using an unwrapped native reader (`ParquetFile`, `pyarrow.dataset`, `np.load`, pickle, sqlite, h5py, memmap, HDF/ORC): **0** [].
Files that import a network client (`requests`, `urlopen`): 5 ['index_data/instruments.py', 'scanner/equity.py', 'scanner/nse_fo.py', 'scanner/sectors.py', 'scanner/universe.py']; they were imported but **no network call was made** - the rerun ran with every socket blocked and nothing raised. Files containing the word "sealed": 1 ['stress_audit/build_report.py'] - in that file it is report text, not a path or an access.
**Conclusion:** coverage is **demonstrated for the Parquet option files and the S1 inputs** (both expected lists are checked against the hashed set, see the table) and **evidenced but not proven for everything else** (the bhavcopy and other cache files rest on the open() hook alone; stat-only access is invisible).

## 6. Missing amendments recorded (correction 6)
`AMENDMENTS_A5_A8.md` records, retrospectively and labelled as such: A5 the join fan-out error of the first S1 run and its fix, A6 the C7 implementation deviation, A7 the G1 audit size (23, not 20),
A8 the provenance-code and report-builder changes made after the first results. They document; they do not authorise anything after the fact.

## 7. Other statements of the original corrected here
| Original | Correction |
|---|---|
| PREREG section 6: the sealed dataset's existence "is noted from the repo's own file names in FINAL_TEST_PLAN.md only"; section 0 "not opened, listed, read or hashed" | Incorrect. At 17:42:23 IST on 13 Nov, one minute before approval, the assistant listed the sealed folder (`ls`, `du -sh`) and read FINAL_TEST_PLAN.md. See DISCLOSURE_REGISTER.md D3. No sealed file was opened. |
| STRESS_REPORT.md header: "Offline: existing files only. No ... live server or VM was changed." | Incomplete. The audit window contains 5 `git pull` and 4 `git push` (GitHub) and one `ssh ... echo` to the VM. D1, D2. |
| experiments.csv row E-20261113-02 note: "Offline; sealed expiry data untouched; one stray ssh 'echo' to the VM ... (no data read, nothing changed)" | The ssh command could not read data, but its outcome is unverified (output discarded); git pull/push and the pre-approval sealed listing are not mentioned. D1-D3. |
| STRESS_REPORT.md section 14: "input files with sizes and SHA-256 in RUN_MANIFEST.json" | Only the 13 S1 inputs were hashed there; full coverage is in MANIFEST_SUPPLEMENT.json (section 5). |
| STRESS_REPORT.md was built by a build_report.py committed (136d3de6f) after the manifest's commit (3fa031ee3) | Recorded in A8; the only difference is one sentence in section 6. |
| REVIEW_REPORT.md header: "committed locally and NOT pushed" | True when written (20:01 IST); **untrue since 21:44:07 IST**, when another session pushed `939f7eef3`, which carries both review commits to origin/main. I did not push. See DISCLOSURE_REGISTER.md D14. |

### 7a. The sealed folder: separate events, not to be conflated (point 3)
| | Event | When (IST, 13 Nov 2026) | Exact path | What happened | Evidence |
|---|---|---|---|---|---|
| A | **Earlier access (a disclosure, not softened)** | 17:42:23, one minute before approval at 17:43:55 | `C:\Users\sherw\project-f-0\expiry_research\data\sealed` (run with `cd` into `expiry_research`: `ls data/sealed | head` and `du -sh data/sealed`); and `C:\Users\sherw\project-f-0\expiry_research\FINAL_TEST_PLAN.md`, lines 1-40 (a plan document in `expiry_research/`, outside `sealed/`) | The folder's directory listing and total size were read: `panel_BANKNIFTY_final.parquet`, `panel_NIFTY_final.parquet`, `panel_SENSEX_final.parquet`, `panel_gaps_final.csv`, `verify` (a sub-folder), total 1.7 MB. **No file inside `sealed/` was opened.** Done to answer "what type of data is sealed?", before the "do not open or inspect" condition existed. | session transcript |
| A2 | Earlier text search (no folder access) | 17:13:39 | `C:\Users\sherw\project-f-0\DECISIONS.md` | a `grep` for the word "sealed" in the decisions file; the folder was not touched | session transcript |
| B | Blocked attempt in the review | 19:24:46 | `C:\Users\sherw\project-f-0\expiry_research\data\sealed` (`ls -la --time=birth` and `stat -c '%y %n'` on its contents) | **blocked by the permission system before it ran**; nothing returned | session transcript |
| C | Provenance reruns in this correction phase | from 21:5x (reruns) | none | the logged file opens, native reader paths and directory listings of the rerun contained **0 paths with "sealed" in the name and no listing of `expiry_research/` or `sealed/`** | `MANIFEST_SUPPLEMENT.json` (`sealed_paths_seen`) |
**What "0 sealed paths" does and does not mean.** It describes event C only. It says nothing about event A, which happened earlier, was a listing of the folder plus its size, and stays on the record. It also cannot see `stat()` calls or reads through unwrapped native entry points (limitations 1 and 2 in section 5). The supporting facts are the static scan in section 5 (the only code file that ran containing the word "sealed" is `stress_audit/build_report.py`, as report text, not a path or an access) and that the loaders the pipeline calls address `options_1m`, `spot_1m`, `options_daily`, `vix_daily` and the S1 files.

## 8. Not corrected, on purpose
- Every number, table and verdict of the original: unchanged and reproduced by the review. - Review items 7 and 8 (tick-aware rounding in the S1 walk; Holm family wording) were outside the six approved corrections and are left as findings.
- The unrecorded first S1 run cannot be reproduced and is not reconstructed. - Strategy rules, parameters, production code, charges, datasets: untouched. - No push, no pull, no VM, no sealed data.

## 9. Conclusions after the corrections (unchanged in direction)
S1 fade v12: insufficient evidence, first-candle range +1.786 % to +3.876 % (precise values; earlier roundings +1.79 % to +3.88 % and +1.8 % to +3.9 %). G1: insufficient evidence, execution-stress robustness split (G1 +5.54 %, t 0.942, interval -5.8 to 17.2 %).
G1-F: in-sample, insufficient evidence for future performance (+19.7 %), not validated.
