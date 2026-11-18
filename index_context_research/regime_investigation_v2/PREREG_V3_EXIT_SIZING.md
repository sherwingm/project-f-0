# Pre-registration: G1-F excursion audit, time-stop and inverse-volatility sizing (18 Nov 2026)

Written and committed before any number of this study. User choice "option 1" after the repeat-research warning: **only the parts not already tested**. Not run here: tighter stops and trailing locks (already tested: `g1_research/VERIFY_RESULT.md` Test 5, `G1C_OPT_RESULT.md` exit cells, stress audit E-20261113-02; `strategies/S3_G1_put_overnight.md:53`). The live rule (50 % stop on the bid, else sell at the next session's close) is the baseline and is not changed. No entry is dropped. No data fetching, missing-bar handling or quote-warning code is touched.

## Data and split
- Trades: the recorded G1-F (154), all 100 % of entries kept. Option minute paths of the recorded contract come from the engine (`scanner/s3_engine.py`, same construction as `interim/agent2_anatomy/build_anatomy.py`, read-only).
- Year 1 = entry days to 2025-09-30 (75 trades); Year 2 = after (79). **Year 2 stays locked** until one candidate is chosen on Year 1, then it is run once. Neither year is blind to the project (G1-F's whole-sample results exist); the 8 best trades earn 77 % of the rupees, so any rule that cuts runners will look bad and any rule that spares them can look good by luck.
- Sibling check: G1 puts (259, G1-F is a strict subset, same entry logic). Year-1 G1 = 128 trades; "G1 outside G1-F" is the independent part. G1-C calls (opposite side) are reported for information only and are not in the gate.

## Step 1: Year-1 audit (descriptive, no rule is chosen from it)
1. MAE (lowest option minute close vs price paid, before exit): distribution for winners vs losers; the MAE level that would have caught the most losers while sparing at least 90 % of winners (reported only).
2. MFE (highest option minute close during the hold) vs the realised net %: giveback, by winners / losers, share of trades whose peak was above +50 % / +100 %.
3. Minutes (market minutes since entry) to first reach +20 % and +50 % unrealised, winners vs losers.

## Step 2: candidate rules (coarse grid, fixed now)
- **Time-stop (T):** after N market minutes from entry, if the option minute close is not above paid x (1 + g), sell at that minute (engine fill, bid side, same costs). N in {30, 60, 120, 240}; g in {0 %, +10 %}. Trades with fewer than N minutes left on the entry day are not time-stopped. The 50 % stop still acts first. 8 cells.
- **Inverse-volatility sizing (S):** size multiplier = clip(R / VIX at the signal minute, 0.5, 1.5) with R in {13, 15}; a second family uses the ATM IV in the dataset with R = Year-1 median rounded to a whole number. Returns in percent do not change; rupees scale by the multiplier (fractional lots assumed, a simplification). 3 cells.
- **Combined (T+S):** each T cell with the better S cell by the same rule below (no new cells).
- Baseline = recorded results.

## Metrics
Trades, win rate, mean net % (per premium), winsorised mean (2 % each tail), profit factor (sum of winning rupees / sum of losing rupees), Sharpe (mean / sd of per-trade rupee P&L x sqrt(trades per year)), max drawdown (rupees, chronological cumulative).

## Selection rule (fixed now)
A candidate passes the Year-1 gate only if: Sharpe and profit factor are both higher than baseline for G1-F AND for G1 outside G1-F (independent siblings), and the mean net % does not fall. Among passers choose the one with the fewest parameters (size alone before time-stop; one time-stop cell before combined); a tie goes to the larger G1-F Sharpe gain. With no passer: no candidate, Year 2 is not opened. The chosen candidate is run once on Year 2 and on G1 Year 2, and the table is printed whatever the outcome. No grid cell is changed after Year-1 numbers.
