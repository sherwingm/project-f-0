# G1-C optimization study: result (14 Nov 2026)

Plan: `G1C_OPT_PREREG.md` (commit `735a27236`; Amendment 1 `168f337ff`, before any by-cell number). Script `scripts/g1c_opt.py` (`8b6ddafe6`, amended `168f337ff`).
Data: NIFTY 1-minute spot and option prices, engine fills, dated STT, 1 lot. 240 call signals simulated 2024-10-01 to 2026-10-28: **discovery 113** (before 2025-10-01), validation 127.
Outputs: `results/g1c_opt_discovery.csv`, `results/g1c_opt_candidates_frozen.csv` (empty), `data/g1c_opt_trades.csv`.

## Verdict: no candidate
- 22 cells had at least 30 discovery trades and were tested; **none survived Benjamini-Hochberg at 10 %** (the best one-sided t was +0.14, needed far higher). GAP075 had 4 trades ("too few").
- No cell was frozen, so the validation half was **not opened** (the script confirms: "frozen candidates: none").
- G1-C stays exactly as it is (live paper, own 30-trade gate). No shadow tag is proposed.

## Discovery numbers (max up first; then booked, % of premium a trade)
Max up is through the next session's close, ATM unless the cell changes the strike.
- **Baseline B (live rule), 112 trades:** max up +50 % on 46 %, +100 % on 21 %, +200 % on 8 %; mean +74 %, median +40 %. Booked: win 30 %, mean -4.35 %, median -51.3 %, t -0.56, -6.4 % at 2x costs. Total +Rs 23,239 (positive in rupees though negative per trade: a few large winners on dearer premiums).
- **Exits:** same day 15:15 -6.7 % (t -1.57); next 09:16 -2.1 %; two sessions -6.1 %; 35 % stop -2.1 %; no stop -2.5 %. All negative.
- **Strikes:** 1 ITM -0.9 %, 2 ITM -1.2 % (smaller losses, fewer big doubles: +100 % on 17 % / 15 %). Same pattern as the earlier ATM-vs-ITM check.
- **Skip filters (14 cells):** best four, all well short of significance: keep wider ranges +1.6 % (t 0.14), keep lower VIX +1.1 % (t 0.10), keep early breaks -0.2 %, keep deeper breaks -3.8 %. Every cell is negative or near zero at 2x costs.
- **From the user's notes (Amendment 1):** gap-and-go (gap >= +0.75 %): 4 trades, too few. Skip the "small gap + 2.5 % above the 20-day average" days: it removes only 4 trades and leaves -3.2 % (t -0.40).

## Reading
- Calls on the first up-break reach big moves often enough (a +100 % peak on about 1 in 5) but the booked result stays negative whichever exit, strike or entry-time filter is chosen. This matches the earlier verification (ATM -10.8 % over the whole window).
- Nothing in this family gives a reason to change G1-C. The forward paper record (1 of 30 trades) remains the only fresh evidence.
- Not tested here (outside the rules or a separate decision): spreads with a sold leg, option selling around events.
- Caveat: the whole window had been looked at for calls before this page; a pass would have been weaker than a clean test. The registry counts 23 cells.
