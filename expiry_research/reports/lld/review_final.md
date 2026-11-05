# LLD: review_final (skeptical review of the final test and the tradeability step)

Written 2026-11-05 before the review code. Code `scripts/review_final_checks.py`; outputs `results/review_final/`.
Reads: `results/final/*`, `results/tradeability/*`, the frozen candidate files, and raw data in the store
(`spot_1m`, `options_daily`, `options_1m`, `vix_daily`). Writes nothing outside `results/review_final/`, this LLD and
the script. No S1/S2/S3 code; `server/charges.py` read for its formula only (not imported).

## Checks
1. **Features from raw.** For each of the 13 candidates, 5 final-period sessions (flagged first, then nearest the
   threshold, both sides). My own code, from raw files only:
   - spot daily OHLC from `spot_1m` (09:15..15:29 bars; duplicates by minute: count them, keep first in file order
     and also report if the other source changes the value); close(t) = 15:29 bar close.
   - f_mom5 = close(t)/close(t-5) - 1; o_cc = close(t)/close(t-1) - 1; streak of close signs; ATR14 % = mean true
     range of 14 sessions ending t / close(t).
   - Bhavcopy of t: front future (expiry > t) volume, ratio to mean of the previous 20 sessions; near option
     expiry (first > t): call wall (strike above close with max CE OI), put wall (below, max PE OI), wall_width,
     wall_near, PCR OI, ATM straddle settle % of close, dte, n_sess (weekdays t+1..expiry), iv_proxy, iv_chg.
   - Targets of t+1: max excursion vs close(t) >= 1 %, range %, low vs close(t).
   Compare with `flags_<UL>.csv` (feature, flag, target). Tolerance 1e-6 relative.
2. **Gates.** Recompute gate 1, BH q over the 13 one-sided p-values, the label; from `flags_<UL>.csv` recompute n, k,
   base and the one-sided p (binomial / t). Confirm thresholds equal the frozen files.
3. **Fills.** 8 trades from `trades.csv` (mix: expiry a/b, exits i/ii/iii, D0 and a +20 % hit), each by hand from
   the raw `options_1m` files: 09:15 spot open, strike, expiry, 09:16 closes, exit minute and prices, slippage,
   charges (formula from charges.py), net %, max up.
4. **Look-ahead.** Entry minute 09:16 > signal time (TCLOSE of t); strike uses the 09:15 open only; target exit
   uses minute closes after entry; every trade_date > signal_date. Spot 09:15 duplicate rows: does the strike change?
5. **Claims.** Compare report sentences with the CSVs (overstatements, missing caveats).

Verdict per item: confirmed / issue (severity). Nothing is re-tuned, no new candidate.
