# Date-versioned STT: effect on the G1 history (2026-11-13)
Change: `server/charges.py` `STT_HISTORY` + `leg(..., on=date)`; `scanner/s3_engine.py` passes each leg's own trade date. Live and every caller that passes no date are unchanged.
Rates used (secondary sources, Finance Acts not read; see `docs/research/SOURCES.md`): options sale STT 0.0625 % before 2024-10-01, 0.10 % from 2024-10-01, 0.15 % from 2026-04-01 (futures 0.0125 / 0.02 / 0.05 %; exercise 0.125 / 0.125 / 0.15 %). Other components not versioned (exchange charge Rs 35.03 per lakh from 2024-10-01 per NSE circular NSE/FA/64232 versus the Rs 35.53 used for all dates: not confirmed, about Rs 0.5 per lakh).

Replay of the live rule (ATM put, 50 % stop, next-close exit, 1 lot, engine fills), 2024-10-01 to 2026-10-28, old single table versus dated STT:
- G1 (259 trades): total Rs 40,448 -> Rs 41,309 (+Rs 861); average fees per trade Rs 68.1 -> 64.8; average net 5.49 % -> 5.53 %; win rate 34.4 % unchanged.
- G1-F (154 trades): total Rs 247,046 -> Rs 247,602 (+Rs 556); average net 19.66 % -> 19.70 %; win rate 40.9 % unchanged.
- No trade changed from loss to win or back; the largest single-trade change is Rs 27.84.
Conclusion: the old single table over-charged older trades slightly (conservative) and no recorded verdict changes. Result files written before 2026-11-13 were NOT recomputed or overwritten. Scratch script: not kept (the numbers above are from a read-only comparison run).
