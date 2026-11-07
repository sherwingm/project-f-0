# G1 / G1-F research (normal index put; its own storage, not mixed with expiry_research/ or near_tighty_research/)
- `data/g1_maxup_free_trades.csv`: every G1 history trade from 2025-01-01 with its max up after entry, no stop and no exit, in three windows (entry day, to next 09:16, to next close); `g1f = 1` for the G1-F trades.
- `results/g1_maxup_free_summary.csv`: the same as shares reaching +25 / +50 / +100 / +200 %, G1-F (main) and G1, 2025 and 2026.
- `scripts/g1_maxup_free.py`: reproduces both (`INDEX_STORE=../fo-index-data/data/index`).
Rules: `strategies/S3_G1_put_overnight.md`. The measure is max up after entry, not an exit (the user, 2026-11-06).

## SENSEX and call side (2026-11-06, the user: "add the SENSEX too", "do the call buying too by inversing the rule")
All max up after entry, no exit, history Oct 2024 -> Oct 2026 (windows: entry day, to next 09:16, to next close).
- `scripts/sensex_maxup_free.py` -> `data/sensex_maxup_free_trades.csv`, `results/sensex_maxup_free_summary.csv`: the G1 / G1-F put rule on SENSEX (step 100).
- `scripts/calls_maxup_free.py` -> `data/calls_{nifty,sensex}_maxup_free_trades.csv`, `results/calls_{nifty,sensex}_maxup_free_summary.csv`: the mirror (first close ABOVE the range -> ATM call), NIFTY and SENSEX. "Mirror filters" = skip gap <= -0.3 %, width 0.5-0.8 %, VIX >= 17: a guess by symmetry, not tested knowledge.
Entry price = minute close x 1.005 (x 1.01 before 09:30), not the engine's fill, so the NIFTY call figures are not exactly comparable with the NIFTY put file.

**Reporting default (the user, 2026-11-07):** results lead with max up after entry (share reaching +50 / +100 / +200 %, mean, median), then the booked result.
