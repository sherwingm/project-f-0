# G1 follow-through vs FII / DII positions, news tone, heavyweights: result (2026-11-08). Plan: EXTERNAL_PREREG.md. Script: scripts/g1_external.py
638 signals (2021-11 to 2026-10), outcome = NIFTY kept falling >= 1 ATR5 from entry to the next close. Periods: discovery 248, validation 127, confirmation 263.

## Data actually used
- NSE participant-wise open interest (FII, DII, Client, Pro in index futures and options): 1,280 daily files, Sep 2021 to 6 Nov 2026. Positions of the previous session close.
- GDELT daily news tone and coverage for "Nifty OR Sensex OR Indian stocks" (2021 to 2026). A global, machine-scored, noisy proxy for sentiment.
- Daily bars of the 11 heaviest NIFTY stocks (about 60 % weight, fixed approximate weights): previous-day and 5-day returns, today's open gap, breadth, bank vs rest.
- NOT available: FII / DII cash-market buy / sell by day for the history (NSE gives only the latest day). Not tested; a gap, not a hidden result.

## Result: 0 candidates in 54 single rules (best q = 0.105; bar 0.10)
Best in discovery, then what happened later (share reaching >= 1 ATR, bucket vs the rest):
| Rule | Discovery | Validation | Confirmation |
|---|---|---|---|
| DII index futures net: higher | 17 % vs 36 % | 26 % vs 33 % | 36 % vs 48 % |
| FII index futures change, 1 day: fell | 40 % vs 24 % | 38 % vs 26 % | 39 % vs 36 % |
| Heavyweights' 5-day return: negative | 39 % vs 24 % | 24 % vs 32 % | 40 % vs 36 % |
| Heavyweights down yesterday (7+ of 11) | 38 % vs 24 % | 27 % vs 31 % | 44 % vs 33 % |
| News tone rising | 22 % vs 33 % | 24 % vs 33 % | 45 % vs 32 % |
- The FII one-day futures change (FII cutting longs or adding shorts) kept the same direction in both later periods but the gap faded (+14 -> +12 -> +3 points): a weak lead, not a result.
- News tone flipped sign in the confirmation period: not stable.
- Caveat: raw position levels drift over the years (DII net moved a lot), so a cut-point set on the first two years puts most later days in one bucket (242 of 263 in confirmation). A drift-free form (position vs its own recent range) is a different test and would need its own written plan.
