# S1 Arm B · longer-hold exits, and is the profit just the NIFTY rising? (pre-registration, 10 Nov 2026)

Numbers only. Nothing live changes. Written BEFORE any number of either part is computed.

**Why.** Arm B's 2023-24 and 2025-26 backtests lose in every hold of 1-10 sessions and win only in the few trades that
reach 11+ sessions (`DECISIONS.md` v7 / v8; re-run 10 Nov). That group is selected by surviving the 50 % stop and the
5-session decay, so it proves nothing by itself. The user also guesses that the live paper account's recent gains come
from NIFTY rising after 28 Oct (22,699 -> 25,045 on 9 Nov, +10.3 %), not from the rules.

**Already looked at (so a pass is weaker than a clean one).** The held-sessions table of Arm B for 2023-24 (events
2023+ only: the 2021-22 results events are not on this PC) and 2025-26. Part 1's holdout run is therefore a re-use of
data already seen; it is stated, not hidden.

## Part 1 · Arm B with a longer hold

Base = the live paper rules (v7 `old_expiry`: current monthly kept only with >= 10 sessions left, normal band
Rs 600-8,000, >= 50 contracts on day +1, entry at day +1 VWAP + 1 tick, one position per stock, 10-session cooldown).
Signals = Arm B exactly as already run: v7's strong-sector beats for 2023-24, v8's arm B for 2025-04-01 to 2026-09-25.
Only the exit changes. Variants (all exits at a close, price = close - 1 tick, net after real charges and % slippage):

| name | exit |
|---|---|
| LIVE | v7 exit as run today: 50 % stop at a close, 5-session decay, T-1 (the reference, re-run in the same code) |
| H8 | no stop, no decay: sell at the close of session 8 after entry (T-1 if the expiry comes first) |
| H11 | the same at session 11 |
| S8 | no stop and no decay for the first 8 sessions; from session 9 the LIVE rules (50 % stop, 5-session decay counted from session 8, T-1) |

**Report per variant and period (2023-24; 2025-26 holdout; 2025 / 2026 halves):** N, win %, mean and median net % of
premium, total Rs, date-clustered t, % of trades that closed at <= -50 %, worst trade, share of total profit from the
top 3 trades.

**Pass (fixed now), per variant:** mean net % > 0 with date-clustered t >= 2 in 2023-24, AND mean > 0 in the 2025-26
holdout, AND mean above LIVE's in both, AND the result does not vanish when the top 3 trades are removed (mean still
> 0). Anything less = no. A pass only justifies a paper shadow tag (the user's decision), never a live change.

## Part 2 · is the profit the NIFTY rising?

For every trade of: v7 2023-24 (old_expiry and primary, arms A, B), v8 2025-26 (arms A, B, S, S_miss), the fade
backtests that carry day-0..exit dates (`S1_v12_exit_trades.csv`) and the live paper ledger (closed and open, S1 arms
and fade), compute NIFTY 50's return from the entry-day close to the exit-day close (open trades: to the 9 Nov close;
data: Upstox public daily candles).

1. Correlation of net % with that NIFTY window return, per group.
2. Mean and win % of net % by NIFTY-window tercile (down / flat / up), terciles from all trades pooled.
3. Slope and intercept of net % on NIFTY return (OLS): the intercept is what the rule earns at a flat NIFTY.
4. For the live ledger: each trade open at any time since 28 Oct, its P&L against NIFTY from 28 Oct, and the account's
   total split into trades opened before vs after 28 Oct.

**Reading rule (fixed now):** "explained by NIFTY" = the group's mean net % is positive only in the up tercile AND the
intercept (flat NIFTY) is <= 0 or its confidence interval includes 0. If instead the mean is positive in the down and
flat terciles too, the profit is not just the market. With a short live record the live part is descriptive only.

## Files
`scanner/armb_hold_and_nifty.py` -> `data/results/S1_armb_hold_and_nifty.md` and `_trades.csv`.
