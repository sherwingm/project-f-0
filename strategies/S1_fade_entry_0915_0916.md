# S1 fade · entry at 09:15 or 09:16? (pre-registration, 11 Nov 2026)

Numbers only. Nothing live changes. Written BEFORE any number of this test is computed. The user: "check the entry time we have been fighting between 9:15 and
9:16, with the Oct 2024 minutes and the recently collected data in seconds".

**Part 1 · minute candles, Oct 2024 - Sep 2026.** The fade live-rule trades (the 326 with a known strike of `S1_fade_minutes_retest`, price >= Rs 2, lot Rs 600-8,000
at the 09:16 entry). Entry E16 = the 09:16 candle's open + 1 tick (the current test entry). Entry E15 = the 09:15 candle's open + 1 tick (the day's first print).
Exit v12 (live): -20 % stop, 2 % trail once +10 %, else the 15:19 close; checks start with the candle AFTER the entry candle (09:16 for E15, 09:17 for E16);
also v10 (hold to 15:19). A trade is compared only when BOTH entries are buyable (candle exists, price >= Rs 2, lot Rs 600-8,000). Real charges.
Report: n, mean / median net %, win %, total Rs, the paired mean difference (E15 minus E16) with date-clustered t, both half-years; and the mean entry price
difference (E15 / E16 - 1) and the 09:15 candle's range as % of its open.

**Part 2 · second candles, 26-30 Oct 2026** (`data/candles_1s`, traded and BID/ASK per second). The 23 live fade trades of those days (all have their contract
recorded). Fills: buy at the ASK, sell at the BID (the real spread). Entry times: 09:15:01, 09:15:10, 09:15:30, 09:15:55, 09:16:00, 09:16:30, 09:17:00 (the last
recorded second at or before that time). Exit as the live v12 on the bid path: sell at the first bid <= 0.80 x entry; trail on once a bid >= 1.10 x entry,
then sell at a bid <= 0.98 x the highest bid since; else the 15:20 bid. Bid low is used for the stop, bid close for the trail. Not buyable if there is no ask yet,
the ask < Rs 2, or the lot is outside Rs 600-8,000. Report per entry time: buyable n, mean / median net %, win %, mean spread paid at entry (ask vs bid), and the
live fills' own times for reference.

**Decision rule (fixed now):** an entry time is called better only if its paired mean difference is > 0 with t >= 2 in Part 1 AND it is not worse in Part 2.
Otherwise the two are not shown to differ. Any change to the live entry time is the user's decision.

**Caveats stated now.** Part 2 is 23 trades in 4 days, all in a rising market: descriptive only. The 09:15 candle's open may not be buyable at the open (the
opening auction print); the seconds data shows what an ask actually was. Part 1 uses only trades that were buyable at 09:16, which may favour E16.
