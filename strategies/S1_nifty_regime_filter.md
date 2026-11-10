# S1 · NIFTY regime filter (pre-registration, 10 Nov 2026)

Numbers only. Nothing live changes. Written BEFORE any number of this test is computed.

**Why.** `S1_armb_hold_and_nifty.md` found S1 arms A and B earn nothing at a flat NIFTY: the result follows NIFTY's move over the
trade. The user asks: buy only when NIFTY is in an uptrend.

**Filter (one, fixed now).** On the signal day (day 0), after its close: NIFTY 50 close > its simple average of the last 50
sessions' closes (day 0 included). Known before the day +1 entry, so no look-ahead. Not tuned: 50 sessions was named by the user.
No second filter, no other lengths, no re-fitting after seeing results.

**Trades.** The LIVE-exit trades already simulated for arms A and B (v7 `old_expiry` rules) in
`data/results/S1_armb_hold_and_nifty_trades.csv`: 2023-24 (A 162, B 57) and the 2025-26 holdout (A 177, B 74). Nothing is
re-simulated; the filter only selects trades by their signal date. NIFTY daily closes: Upstox public candles.

**Report, per arm and period:** trades kept vs dropped: N, win %, mean and median net % of premium, total Rs, date-clustered t,
mean with the top 3 kept trades removed; also the share of signal days passing the filter and the NIFTY return over the kept
and dropped trades' windows (to show how much of any gain is just the market).

**Pass (fixed now), per arm:** kept mean > 0 with t >= 2 in 2023-24, AND kept mean > 0 in 2025-26, AND the kept mean above the
dropped mean in both periods, AND the kept mean still > 0 without its top 3 trades. Anything less = no. A pass would justify only a
paper shadow tag (the user's decision), never a live change.

**Caveats stated now.** The idea comes from seeing that profit follows NIFTY, found in these same trades: weaker than a fresh
test. 2023-24 covers events from 2023 only. A trend filter on a market that rose for most of both periods may keep most trades.

Output: `scanner/nifty_regime_filter.py` -> `data/results/S1_nifty_regime_filter.md`.
