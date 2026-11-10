# S1 · does a nearer or farther strike do better? (pre-registration, 10 Nov 2026)

Numbers only. Nothing live changes. Written BEFORE any neighbour-strike minute number is computed. The user asked to test whether a nearer or farther
strike than the walk's pick would have done better, for the fade and for Arm A/B.

**Trades.** Fade: the 326 live-rule trades of `S1_fade_minutes_retest` that have a known strike (entry 09:16 open + 1 tick, price >= Rs 2, lot Rs 600-8,000).
Arm A/B: the 140 trades of `S1_armab_minutes` (Oct 2024 on; arm A, arm B is a subset). Same signals, same days, same side and expiry.

**Neighbours.** For each trade the two listed strikes nearer the money (offset -2, -1; more expensive) and the two farther (+1, +2; cheaper), from the day-0
chain of that stock and expiry, counted in LISTED strikes. 1,303 fade and 545 Arm A/B neighbour contracts; 1-minute candles from Upstox (fade: day 0;
Arm A/B: entry day to expiry), fetched by the `stock-options-probe` workflow (`nbrfade`, `nbrab`).

**Rules for each neighbour (unchanged from the pick):** entry 09:16 candle open + 1 tick; excluded if no 09:16 candle, or the price is < Rs 2, or one lot is
outside Rs 600-8,000 (counted per offset: "not buyable"). Exits: fade v12 (live) and v10; Arm A/B LIVE-CLOSE and H8. Same charges and slippage.

**Report per offset (-2, -1, 0 = the pick, +1, +2):** buyable n, win %, mean, median, total Rs, date-clustered t; and the PAIRED comparison on trades where both the
pick and the neighbour are buyable: mean difference (neighbour minus pick) and t. Fade also by side (put / call).

**Pass (fixed now), per offset:** paired mean difference > 0 with date-clustered t >= 2 AND positive in both half-years AND the offset's own mean > 0. A pass
would only justify a paper shadow tag (the user's decision), never a live change. Anything else = the walk's pick is not shown to be beatable.

**Caveats stated now.** Neighbours are cheaper/dearer, so the lot band and the Rs 2 floor remove different trades at each offset (reported). 326 and 140 trades.
The volume cut-off (50 vs 100 lots) was tested separately (`S1_fade_novolume`, `S1_fade_vol100`): it moves 3-5 % of picks and is not repeated here.
