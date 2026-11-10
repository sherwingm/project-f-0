# S1 strike choice, a 09:16-knowable volume rule, and the next strike when the pick has no 09:16 trade (pre-registration, 11 Nov 2026)

Numbers only. Nothing live changes. Written BEFORE any of these numbers is computed. The user (11 Nov 2026), on the
weak points of the one-contract pick:
- "just find the limit of how much vol should be there at the 9 16 or before"
- "try the results by choosing the next strike, and mainly check the news that whether it is banned"
- "[one strike per signal, no check of nearer or deeper in-the-money strikes] check that"
- The Rs 2 floor is kept: the 19 Oct 2026 floor sweep (`data/results/S1_v10_floor_sweep.md`) already showed the
  trades under Rs 2 lose (mean -14 % to -16 %, median -28 % to -30 % without the one KALYANKJIL outlier).

## Data
- **Fade signals:** the 468 in `data/results/S1_fade_realistic_entry_trades.csv` (day 0 17 Oct 2024 - 17 Aug 2026; the
  v10 signals, expiry and strike walk of `scanner/backtest_s1_v10.py`; 59 of them have no 09:16 candle on the pick).
- **Strikes fetched (day 0 only, Upstox expired 1-minute candles):** for each signal, on that day's chain (bhavcopy,
  same expiry and side): the two strikes in the money next to the at-the-money one (ITM2, ITM1), the at-the-money
  strike (the walk's start), and every strike of the walk from there to 3 past the pick (walk +1, +2, +3). The pick's
  candles are already in `S1_v10_bandv10_minutes.csv`; the 1,291 strikes that the neighbour test
  (`strategies/S1_strike_neighbours.md`, another session, 10 Nov) already fetches are read from its file
  `S1_v10_bandnbrfade_minutes.csv`, not fetched again. The other 2,822: `S1_v10_bandstrk{1,2}_contracts.csv` (two
  GitHub runs: Upstox allows 2,000 calls per 30 minutes).
- **Overlap with the neighbour test:** it compares the pick with 2 strikes nearer and 2 farther, with the lot band kept.
  Test 1 here adds the in-the-money strikes, at the money and walk +3, without the lot cap, on the 468 signals; where the
  two tests share a strike, both read the same candles.
- **Arms A / B:** the 77 trades of `S1_armab_minutes` dropped for "no 09:16 candle": the next listed call strike above
  the pick on the entry day's chain, same expiry, candles from the entry day to expiry
  (`S1_v10_bandabnext_contracts.csv`).
- **Ban list:** `data/events.sqlite`, type `ban`, subtype `in` (NSE `fo_secban` files). A stock in the F&O ban on the
  entry day cannot open a new position, so such a trade is dropped and counted. Known so far: RBLBANK 2025-10-20 (fade).
  The store has ban rows on 210 of 493 sessions in the window; a day with no rows is read as "nobody in ban" (stated
  as a limit: a missing file looks the same).

## Fixed rules (same as the v12 backtest, `scanner/fade_stop_trail.py`)
- Entry: the strike's 09:16 candle open + 1 tick (Rs 0.05 before 2025-11-03, Rs 0.01 from it). No 09:16 candle = no
  entry on that strike.
- v12 exit: -20 % stop touched by a candle low from 09:17 (fill min(stop, open) - 1 tick); trail on once a candle high
  reaches +10 %, then sell when a later candle low touches 0.98 x the highest high (fill min(level, open) - 1 tick);
  else the 15:19 close - 1 tick. Real charges (`server/charges.py`), 1 lot, no slippage term (as the v12 backtest).
- Halves: train = day 0 before 2025-11-03, test = from it (as the v12 study). t is date-clustered.

## Test 1 · which strike (fade, v12)
Rules compared on the same signals: ITM2, ITM1, ATM, walk -1 (one closer), the walk pick, walk +1, walk +2, walk +3.
No lot-cost cap for the alternatives; the share of trades over Rs 8,000 a lot is reported.
**Pass (fixed now):** a rule beats the walk pick only if, paired on the same signals, the mean difference in net % is
> 0 with t >= 2, > 0 in both halves, and its total Rs is higher too. A rule that breaks the Rs 8,000 budget on more than
half its trades is reported as "over budget", not as a fix.

## Test 2 · a volume rule known at 09:16 (fade, v12)
The walk unchanged except the liquidity check: instead of ">= 50 contracts on the whole of day 0" (not known at 09:16),
">= X contracts traded in the 09:15 candle" (Upstox volume / lot), X in {1, 2, 5, 10, 25}. Rs 2 floor and the Rs
600-8,000 lot band on the 09:16 open + 1 tick, as now. The walk goes from the at-the-money strike outward; strikes past
walk +3 were not fetched, so a signal whose new pick lies there is counted as "beyond the fetch" and dropped.
**Choice (fixed now):** X is picked on train by the highest mean net % (ties: the smaller X) and judged on test against
the current whole-day rule on test. Reported for every X: trades, mean, median, win %, total Rs, t, and how often the
pick differs from today's.

## Test 3 · the next strike when the pick has no 09:16 trade
- **Fade:** for the 59 signals without a 09:16 candle on the pick, take the next strike of the walk (further out) that
  has a 09:16 candle and passes the same checks (>= 50 contracts on day 0, Rs 2, lot band), up to walk +3. v12 exit.
  Reported alone and added to the 409.
- **Arms A / B:** for the 77 dropped trades, the next call strike up, entry its 09:16 open + 1 tick on the entry day,
  the exits of `strategies/S1_armab_minutes.md` (LIVE-CLOSE, LIVE-INTRA, H8, H11, S8), same charges and slippage. Reported
  alone and with the arms' totals. Side line (no decision): the same dropped trades entered on the SAME strike at its
  first candle after 09:16 (up to 09:30), from data already on file.
- **Ban:** every set reported with ban-day trades dropped.
**Pass:** none; this measures what the dropped trades would have made. A rule change needs the user.

## Caveats stated now
- Upstox fills quiet minutes with zero-volume candles after a contract's first trade (61 % of the arms' candles have
  volume 0), so "a 09:16 candle" means "traded at or before 09:16", and its open can be the 09:15 close.
- 22 months, one exit (v12), one data source. The v12 2 % trail was chosen after seeing part of this data.
- Two signals' rebuilt walk does not land on the stored pick (chain differences); they are reported, not fixed.
- Contracts Upstox does not return are dropped and counted.

Output: `scanner/strike_choice_minutes.py` -> `data/results/S1_strike_choice_minutes.md` (+ `_trades.csv`).
