# S1 · extension of the minute-candle backtests to Sep - Oct 2026 (pre-registration, 14 Nov 2026)

Numbers only. Nothing live changes. Written BEFORE any extension number is computed. The user asked to re-run the S1 backtest and fetch the missing data.

**New data fetched 14 Nov 2026 (before this page):** NSE F&O files 28 Sep - 13 Nov (3 holiday gaps), results events 10 Aug - 13 Nov (`scanner.events.run --backfill`),
stock daily closes to 13 Nov (eod2). Stock closes and F&O files only choose the signal and the strike; every outcome is on 1-minute candles.

**What is new and what is not.** The earlier minute tests ended with signals of Sep 2026. The extension adds signals from 2026-09-26. It is a true out-of-sample
check of rules fixed long before: nothing below is tuned on it. The live paper account holds the trades from 22 Oct, so the fade extension stops at day 0 = 2026-10-21;
Arm A/B stops at the last day 0 whose expiry's T-1 and 20 sessions fit inside the data (about 14 Oct; November-expiry trades are not finished).

**Rules (unchanged).** Fade: the v10 walk (strong results -> put, weak -> call; start strike nearest the previous close, away from the money, >= 50 lots on day 0, fill
>= Rs 2, one lot Rs 600-8,000), entry 09:16 candle open + 1 tick, exit v12 (-20 % stop from 09:17, 2 % trail once +10 %, else 15:19) and v10. Arm A/B: the v7/v8 `old_expiry`
rules (strike walk, >= 50 lots on day +1), entry day +1 09:16 open + 1 tick, LIVE-CLOSE exit (50 % stop and 5-session decay judged on the daily close, T-1) and H8 as before.
Real charges and slippage. Contracts that Upstox has no minutes for, or with no 09:16 trade, are dropped and counted.

**Report:** per rule, the extension alone (n, win %, mean, median, total Rs, t) and the earlier window + extension together; max up first (share >= +50 / +100 / +200 %, mean, median)
for the fade and Arm A/B, then the booked result.

**Pass / verdict:** none new. The fade extension is read against the earlier +2.9 % (t 1.8): "holds" if the extension mean is > 0, "fails" if <= 0. Arm A/B: "holds as a loser" if the mean is < 0.
Caveats: the extension is small (weeks), so its t will be low; a single window cannot confirm or reject.
