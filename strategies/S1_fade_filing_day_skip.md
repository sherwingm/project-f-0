# S1 fade · use the filing day of a market-hours result to skip losing fade trades (both sides)

**Pre-registered 2026-10-20**, before the counts or results of this rule are computed. The user's request: "keep the
normal trade of fade as it was. With the help of market hrs result can we reduce our loss... for good result too...
if there are too few, stop it at the beginning". **Nothing live changes.** A pass becomes a candidate filter for the
user's decision, with its own version and a DECISIONS.md entry.

## What is not changed
Every fade trade is taken as now: v10 entry, and v11's exit live. This rule can only **skip** some trades whose results
were filed in market hours (09:15–14:50). Filings at other times (after the close, before the open, 14:51–15:30) are
never touched.

## The filing-day watch
- **Cases:** `data/results/S1_intraday_cases.csv`, F&O filings 09:15–14:50 on a session day, with 1-minute candles
  (`S1_intraday_minutes.csv`).
- **D** = the stock's move from the close of the minute before the announcement to the filing day's 15:29 close,
  minus NIFTY 50's over the same minutes. Known at the close, before the fade buys the next morning.
- **D_bet** = D in the fade's direction: −D for a put (strong results, a bet on a fall), +D for a call (weak
  results, a bet on a rise).

## The skip rule (the reversal idea, both sides)
Skip the fade trade when the filing day **already moved at least 2 % the fade's way** (D_bet ≥ +2 %):
- a put after a strong result whose stock already fell ≥ 2 % that day;
- a call after a weak result whose stock already rose ≥ 2 % that day.

The idea: the move is used up, so the next day reverses against the trade. Its mirror (D_bet ≤ −2 %, the day moved
against the fade) is reported, not tested.

Disclosure: a related split without a threshold was already seen (the "loss question" table in
`data/results/S1_intraday_results_reaction.md`), so this is not blind.

## Trades
- The v10 backtest's fade trades with entry = open and E1 (15:20), 2022-26 (`S1_v10_trades_2022_24.csv`,
  `S1_v10_trades.csv`), matched to a case on symbol and filing date.
- v11's exit (−20 % stop from 09:16) on minutes for the same trades from Oct 2024
  (`scanner.fade_armA_filter.v11_minutes`).

## Step 0 · count gate (run first; stop here if it fails)
The **skip group** (D_bet ≥ +2 %) must have **at least 30 trades pooled and at least 10 in each window** (2022-24 and
2025-26). If not, the study stops: only the counts are reported, and no result is computed.

## Pass test (only if the gate passes; all needed)
1. The skipped trades' total net ₹ is **< 0 in 2022-24 and in 2025-26** (skipping saves money in each window; v10 E1).
2. The skipped trades' pooled mean net % is < 0 with a date-clustered **t ≤ −2**.
3. Under v11 (minutes), the skipped trades' mean net % is < 0. Required if they number ≥ 10, else only reported.

## Report
- All fade trades: total and mean, with and without the skip.
- Per side (puts / calls), per window.
- The skip group, the mirror group (D_bet ≤ −2 %) and the rest.
- Each with N, win rate, mean and median net %, total ₹ and t.

## Limits
- Market-hours filings are about 30 % of fade trades. The rule cannot help the rest.
- D is measured from NSE's publish minute: a leak before it (seen in 2 of 12 recent cases) makes D smaller.
