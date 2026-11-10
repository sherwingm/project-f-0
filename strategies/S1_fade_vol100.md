# S1 fade · a stricter volume rule: at least 100 lots on day 0 instead of 50 (pre-registration, 10 Nov 2026)

Numbers only. Nothing live changes. Written BEFORE any minute number of the changed picks is computed. The user asked (after the 50-lot result):
"try if that limits more than 100 lots".

**Method.** The v10 fade walk re-run with the day-0 volume minimum at 100 contracts (1 contract = 1 lot) instead of 50; all other rules unchanged
(day 0 from 2024-10-01 to 2026-09-25, contracts expiring from Oct 2024). Step already run: 14 of the 486 picks made at 50 had < 100 lots; the strike
changes for 9 signals and 5 signals drop out (no strike passes). Changed picks: `data/results/S1_fade_vol100_picks.csv`; fetch list `S1_v10_bandvol100_contracts.csv`.

**Test on minute candles** (as S1_fade_novolume.md): entry 09:16 candle open + 1 tick, excluded if no 09:16 candle or outside Rs 2 / lot Rs 600-8,000;
exits v12 (live) and v10; real charges and slippage. Reported: new strike against old strike on the same signal and day; the 5 dropped signals' old picks
(what the stricter rule would have removed); and the whole live-rule set with the stricter rule applied against the 339-trade result (n, win %, mean, median, total Rs).

**Pass:** none; descriptive. Caveat: 9 changed picks, 5 dropped; too few for significance.
