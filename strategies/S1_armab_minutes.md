# S1 arms A / B on 1-minute option candles (pre-registration, 10 Nov 2026)

Numbers only. Nothing live changes. Written BEFORE any minute number is computed. The user (10 Nov 2026): daily-candle tests are not
accepted; redo them on minute candles.

**Window.** Upstox's expired-option minute candles exist only for stock-option contracts expiring from Oct 2024. So the minute test covers
signals whose contract expires from 2024-10-01 to 2026-09-29: 211 contracts (arm A; arm B is 76 of them), entries 17 Oct 2024 - 17 Aug 2026.
Everything before that (the 2023 - Sep 2024 part of the old 2023-24 test) CANNOT be tested on minutes and is dropped, not extrapolated.

**Contracts.** The call each arm already picked (same signal, same expiry, same strike from the strike walk). The pick used the daily volume of
day +1 (>= 50 contracts), which a live bot would not know at 09:16: stated as a caveat, not changed. Minute candles fetched from day +1 to expiry
(`data/results/S1_v10_bandarmab2_contracts.csv` -> `..._minutes.csv`, GitHub workflow `stock-options-probe`, `fetch_band_minutes armab2`).

**Entry (fixed now).** Day +1, the 09:16 candle's OPEN + 1 tick (as the fade's realistic entry B). No 09:16 candle = excluded and counted.
Same charges and %-slippage model as before.

**Exits, each on the minute candles from 09:17 of day +1 (all exits sell at the candle's CLOSE - 1 tick; a stop is hit when a candle's LOW
touches it and fills at min(stop, candle open) - 1 tick):**

| name | exit |
|---|---|
| LIVE-CLOSE | the live rule as the paper account runs it: 50 % stop and the 5-session decay judged on the DAILY close (the 15:29 candle's close), T-1 at its close |
| LIVE-INTRA | 50 % stop checked on every minute (low touches 0.5 x entry), decay on daily closes, T-1 |
| H8 / H11 | no stop; sell at the close of session 8 / 11 after entry (T-1 if the expiry comes first) |
| S8 | nothing but T-1 for 8 sessions, then LIVE-CLOSE |

**Report per arm and variant (and 2024-25 / 2026 halves):** N, win %, mean and median net % of premium, total Rs, date-clustered t,
share at <= -50 %, mean without the top 3 trades, and the INTRADAY max up (highest candle high) and max dip (lowest candle low) as % of the entry
fill, mean and median. Also the entry gap: 09:16 open + tick against the daily VWAP + tick the old test used, mean and median difference.

**Pass (fixed now), per variant:** mean net % > 0 with date-clustered t >= 2 AND mean > 0 in both halves AND still > 0 without the top 3 trades
AND above LIVE-CLOSE's mean. Anything less = no. A pass only justifies a paper shadow tag, never a live change.

**Caveats stated now.** 22 months and 211 contracts (arm B 76): small. The 2025-26 part has been looked at before on daily data. The strikes
come from the daily walk. If Upstox lacks candles for a contract it is dropped and counted; the count is reported.

Output: `scanner/armab_minutes.py` -> `data/results/S1_armab_minutes.md`.
