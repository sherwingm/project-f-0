# FII / DII positions vs NIFTY's next day, all sessions: result (2026-11-09). Plan: EXTERNAL3_PREREG.md. Script: scripts/g1_external3.py
1,228 sessions (discovery 474, validation 244, confirmation 510), 64 rules (16 drift-free features x high/low x two outcomes: next-day direction, next-day big move = |move| >= 0.77 %). Only about 150 discovery sessions have the 60-session history (89 for the 250-session ones), so discovery is thinner than it sounds.

## Direction: nothing. No FII / DII / Client / Pro position says whether NIFTY goes up or down the next day (every direction rule failed validation and confirmation).

## Size (a big move the next day): one clue that nearly passed, no pass
Retail (Client) index-futures net position HIGH versus its own last 60 sessions (client_fut_net_z60 >= 0.745), share of next days with a big move, bucket vs the rest:
| Period | Sessions in bucket | Big move, bucket vs rest | One-sided p |
|---|---|---|---|
| Discovery | 152 | 42 % vs 29 % | (q 0.054) |
| Validation | 86 | 34 % vs 22 % | 0.028 (passes) |
| Confirmation | 209 | 33 % vs 26 % | 0.051 (misses 0.05 by a hair) |
- Same direction in all three periods; the effect fades (+13, +12, +7 points). By the plan it is NOT a pass (confirmation p 0.051).
- The 250-session rank form says the same thing (34 % vs 15 %, 31 % vs 21 %, 31 % vs 25 %; confirmation p 0.08) and is the same fact, not a second one.
- Reading: when retail is unusually net long index futures, the next day tends to be a bigger-move day. It is about size, not direction, and it matches the earlier finding that size clusters. Likely overlap with volatility clustering; not tested as separate.
- Others (FII ratio, DII net) looked strong in discovery and failed or reversed later (DII net high: 45 % vs 27 % in discovery, 26 % vs 26 % in validation).
