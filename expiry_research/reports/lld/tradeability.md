# LLD: tradeability (NIFTY ATM straddle on real option minutes)

Written 2026-11-05, before any straddle price is read. Follows the "Tradeability" part of `FINAL_TEST_PLAN.md`;
nothing there is changed. Adds one benchmark family the user asked for (straddle on every expiry day and every D-1,
no signal). Scripts: `scripts/tradeability_common.py` (loading, pricing, charges), `scripts/tradeability_run.py`
(trades + summaries, one run). Outputs: `results/tradeability/`. Report: `reports/TRADEABILITY_ANALYSIS.md`.

## Inputs (read-only)
| Input | Use |
|---|---|
| `results/final/flags_NIFTY.csv` | signal day t, trade day t+1 (`y_date`), `<id>_flag`, `f_vix_close` (VIX at t) |
| `results/final/final_results.csv` | which NIFTY candidates are Validated (size) |
| `options_1m/NIFTY/<expiry>/<day>.parquet` | option minute bars (close used); no bid/ask |
| `spot_1m/NIFTY50/<YYYY-MM>.parquet` | 09:15 minute open of t+1 (ATM strike) |
| `options_daily/NIFTY/<YYYY-MM>.parquet` | lot size `NewBrdLotQty` for (t+1, expiry) |
| `data/expiry_calendar.csv`, `data/sessions_NIFTY.csv` | NIFTY expiry dates, session list, expiry context |
| `server/charges.py` | formula only (re-implemented, rates copied; not imported) |

Validated NIFTY rules (from `final_results.csv`): PPC032, PPC062, OC13, OC17, OC21, M143, M218, M220.
OC13 and OC21 share one rule (wall_near), so their flags are identical. PPC062 predicts *fewer* big moves; M218 /
M220 predict a *shallower* low. For those three the size view says flagged straddles should do *worse*.
Union "UP5" = any of PPC032, OC13, OC17, OC21, M143 (the rules that predict a bigger move). Extra, labelled as such.

## Data rules
- Option file read once per (expiry, day). Known duplicates: expiry 2026-10-19 has (timestamp, token) pairs from two
  sources (upstox + kotak, prices differ on about 7 % of pairs). Keep the upstox row (the source of every other
  row in that folder); assert no duplicate remains in any file read.
- A minute bar "exists" only if the file has a row for that (strike, type, minute) with close > 0. Nothing is filled
  or interpolated. A trade that needs a missing bar is skipped and written to `skipped.csv` with the reason.

## Trade (per plan)
- Trade day d = t+1 (every final-period `y_date`). Strike K = the multiple of 50 nearest the NIFTY 09:15 minute
  open of d (tie -> lower). Buy CE K + PE K at the close of the 09:16 minute of d.
- Expiry (a) = nearest NIFTY expiry >= d (can be d itself); (b) = nearest NIFTY expiry > d.
  Expiry list: `expiry_calendar.csv`, NIFTY, all kinds. Cross-check: (a) equals `sessions_NIFTY.next_expiry`.
- Days to expiry `dte` = sessions after d up to and including the expiry (0 = expiry day). Buckets 0, 1, 2, 3+.
- Exits: (i) close of 15:15 of d; (ii) first minute 09:17..15:15 whose straddle close (CE + PE) >= 1.20 x entry
  straddle close (gross, before costs), exit at that minute's close, else 15:15; (iii) close of 09:16 of the next
  session d2. For (iii) a contract expiring on d cannot be held to d2: those trades are "not applicable" (listed).
- Slippage per leg, entry and exit: s at normal minutes, 2s before 09:30 or from 15:00 (plan: 0.5 % / 1 %).
  Scenarios s = 0.5 (base), 1, 2 %. Buy fill = close x (1 + slip), sell fill = close x (1 - slip).
- Charges (charges.py formula, 1 lot = lot size from bhavcopy): per order brokerage Rs 20, exchange Rs 35.53 per
  lakh of premium, SEBI Rs 10 per crore, GST 18 % on those three, stamp 0.003 % on buys, STT 0.15 % on sells;
  each component rounded to the paisa. 4 orders per trade. Rates are those effective 2026-04-01, applied to the
  whole period (stated as a limit). No exercise STT: no exit holds through an expiry close.
- Net % of premium = (sell proceeds - buy cost - charges) / buy cost x 100.
- Max up while held = max over held minutes of (straddle close / entry straddle close - 1) x 100, gross. Held minutes:
  09:17 .. exit minute (i, ii); 09:17 of d .. 09:16 of d2 (iii). Minutes where one leg has no bar are left out of the
  path (count kept). Also a net version: max up at the base slippage, if sold at that best minute (minus charges).

## Groups and statistics
Universe per (expiry choice, exit, slippage): all trades that priced.
- Candidates: each Validated NIFTY rule: flagged (flag 1 at t) vs unflagged (flag 0); UP5 union; every day.
- Expiry family (no signal): d is a NIFTY expiry day ("D0"), d is the session before an expiry ("D-1"), other.
  Expiry kind (weekly / monthly) reported for D0.
- Splits: dte bucket; context (D0 / D-1 / other); VIX tercile of t (cut points from all final-period flag rows).
Per group: n, win rate (net > 0) with Wilson CI, mean and median net %, t (stats_utils.t_stat), worst trade,
drawdown (cumulative sum of net % per trade in date order, largest peak-to-trough, in % of one premium), max up
mean / median / share >= +100 %. Flagged vs unflagged: Welch t, one-sided p (flagged > unflagged; for PPC062,
M218, M220 also reported, the size view predicts the opposite sign). All p-values here are descriptive: the
tradeability test is not a gate and has no BH family beyond the per-table note.
Pass statement (plan): a size signal is worth trading only if flagged beats unflagged and flagged mean net > 0.

## Outputs
`trades.csv` (one row per trade x expiry choice x exit, with all three slippage scenarios as columns),
`skipped.csv`, `summary_signals.csv`, `summary_expiry.csv`, `summary_splits.csv`, `run_stdout.txt`.

## Checks (in the script, stop on failure)
No duplicate (timestamp, token) after dedupe; entry straddle > 0; (a) agrees with sessions_NIFTY next_expiry on every
trade day; every trade day is a session in `sessions_NIFTY`; charges re-implementation reproduces a hand example.

## Review fixes (added 2026-11-05, after `reports/lld/review_final.md`; before any code change)
The final review (`results/review_final/`) found one wording error and three unstated design choices. Changes:
1. **Plan pass rule for every rule.** `worth_trading` was left blank for the three smaller-move rules (PPC062, M218,
   M220). It is now computed for every rule with the plan's literal rule (flagged mean net > unflagged mean net and
   flagged mean net > 0). A new column `size_view_consistent` says whether a pass agrees with the rule's own size
   view (a smaller-move rule "passing" for a bought straddle goes against its logic). `tradeability_run.py` is re-run
   once; `trades.csv` must come out byte-identical (only `summary_signals.csv` may change).
2. **Sensitivity, not a new test** (`scripts/tradeability_sensitivity.py`, reads `trades.csv` and the same option
   minutes; writes `results/tradeability/sensitivity.csv` and `sensitivity_stdout.txt`):
   - (a) *Next-minute fill for the +20 % target.* A live order can only fill after the trigger minute closes. Exit
     (ii) is re-priced at the close of the next minute in which both legs have a bar (up to 15:16); if there is none,
     the trigger minute is kept. Trades that did not hit the target are unchanged.
   - (b) *Tick floor on slippage.* Slippage per leg = max(s % x price, Rs 0.05) at entry and exit (NSE tick 0.05).
   Both are shown for the same groups as the headline tables, at s = 0.5 / 1 / 2 %. Descriptive only.
3. Wording: the report says the plan rule is met in one cell (M220, exit iii, both expiries, 0.5 % slippage only),
   explains why that is not a finding, and states the target-fill and tick choices in its limits.
