# S1 fade · the floor, band, target and Arm-A-filter studies re-run with the realistic entry

**Pre-registered 2026-10-20**, before any of these numbers is computed. Follows `S1_fade_realistic_entry.md` (v11 on the
Rs 2+ set fell from +13.8 % to +2.5 % a trade, t 3.0 -> 0.9). The user said: "re-run the floor, band, target and filter
studies with the new 09:16 entry". **Nothing live changes.** Descriptive; any rule change is the user's decision.

## Data and limits
- Only contracts with day-0 option minute candles can be re-priced: day 0 from Oct 2024 (Upstox's history). The 2022-24
  daily-data parts of the old studies cannot be redone and are reported as "not re-priced".
- Contract sets (all in `data/results/`): `S1_v10_bandv10` (old entry >= Rs 2), `S1_v10_band12` (Rs 1-2) and
  `S1_v10_band050` (Rs 0.5-1), each with `_contracts.csv` and `_minutes.csv`; the `...q4` files of the last two are
  included. A contract in two sets counts once (the first set). Contracts were picked by the old entry's price band, so a
  contract whose old entry was in a band but whose new entry is in another is **re-bucketed by the new entry**; contracts
  never picked (old entry outside every band) are missing. Coverage is reported, not fixed.
- Entry **B** = the 09:16 candle's open + 1 tick (tick Rs 0.05 before 2025-11-03, Rs 0.01 from it). No 09:16 candle:
  excluded and counted. Real charges (`server.charges`), no extra % slippage. t is date-clustered (`clustered_t`).
- Exits, same code for every study (as in `scanner/fade_realistic_entry.py`):
  - **v10:** sold at the 15:19 close - 1 tick;
  - **v11:** the -20 % stop (0.80 x entry), fired in the first candle from 09:17 whose low <= the stop, filled at
    min(stop, that candle's open) - 1 tick; else the v10 exit.

## 1. Floor
For floors Rs 2, 1, 0.5 (a trade is kept when its B fill >= the floor and one lot is Rs 600-8,000): N, win %, mean and
median net % of premium, total Rs, t, for v10 and v11, whole period and the two halves (Oct 2024-Oct 2025; Nov
2025-Sep 2026). The old finding being checked: lower floors add trades that hurt or help.

## 2. Band
The same numbers for the B fill bands >= Rs 2, Rs 1-2, Rs 0.5-1 separately (lot rule as above), v10 and v11.

## 3. Target
On the trades with B fill >= Rs 2 and >= Rs 1: a resting sell at B x (1 + T) for T = 25 %, 50 %, 100 %, 200 %, filled
(at the target rounded up to the tick, minus nothing) in the first candle from 09:17 whose high >= target + 1 tick; else
the exit is the v10 exit ("T only") or v11 ("T + stop", the stop wins when both are hit in the same candle). Same numbers
as above beside the no-target v10 and v11 lines.

## 4. Arm-A-overlap filter (O)
On the B trades with fill >= Rs 2, the `strategies/S1_v10_armA_overlap_filter.md` flag O (stock up >= 2 % more than its
sector at the day-0 open, and < 10 % raw; `scanner.fade_armA_filter.flag`). Report keep / drop groups for v10 and v11, both
sides together and puts / calls. The old test, re-asked on v11 B: **dropped trades lose (mean < 0) in both halves, pooled
t <= -2.** Pass = both halves and the pooled t. Small groups (< 20) are reported but cannot pass.

## Reading rules (fixed now)
- Compare each line with its old-entry line recomputed by the same code (entry A) for the same contracts, so the
  difference is only the entry.
- A result counts as real only with t >= 2 and the same sign in both halves. Otherwise it is "not established".
- Whatever B shows is reported, including that nothing is left.
