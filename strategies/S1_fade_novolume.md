# S1 fade · what the 50-lot volume rule changed (pre-registration, 10 Nov 2026)

Numbers only. Nothing live changes. Written BEFORE any minute number of the new picks is computed. The user asked to find how many trades the
"at least 50 lots traded on day 0" rule excluded and whether those would have done well, fetching the needed data.

**Method.** The v10 fade walk was run twice on the same signals (day 0 from 2024-10-01 to 2026-09-25, contract expiring from Oct 2024): once with the
50-lot rule and once requiring only that the strike traded at least 1 lot. Everything else (start strike, walk away from the money, fill >= Rs 2, one
lot Rs 600-8,000) is the same. Result of that step (already run, daily file for volume only to choose the strike): 486 signals trade under both;
the strike differs for 19 of them, and 3 more signals trade only without the rule: 22 new picks (`data/results/S1_fade_novolume_picks.csv`).

**Minute fetch.** Day-0 1-minute candles for the 22 new strikes (`S1_v10_bandnovol_contracts.csv`, workflow `stock-options-probe`, `fetch_band_minutes novol`).

**Test on minute candles.** Entry 09:16 candle open + 1 tick (excluded if no 09:16 candle, or if that price is < Rs 2 or the lot is outside Rs 600-8,000).
Exits: v12 (live: -20 % stop from 09:17, 2 % trail once +10 %, else the 15:19 close) and v10 (hold to 15:19). Real charges and slippage.
Reported: for the 19 changed signals, the new strike against the old strike on the same day (n, win %, mean, median, total Rs, both exits); the 3 new
signals alone; and the live-rule total with the new picks swapped in against the old rule's 339-trade result. Also the 09:16 volume in lots of each new
pick (from the candles) to show how thin they were at entry.

**Pass:** none is used. This is a count and a comparison, descriptive only. Caveat: 22 trades; no significance can come from them.
