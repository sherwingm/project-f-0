# G1 / G1-F research (normal index put; its own storage, not mixed with expiry_research/ or near_tighty_research/)
- `data/g1_maxup_free_trades.csv`: every G1 history trade from 2025-01-01 with its max up after entry, no stop and no exit, in three windows (entry day, to next 09:16, to next close); `g1f = 1` for the G1-F trades.
- `results/g1_maxup_free_summary.csv`: the same as shares reaching +25 / +50 / +100 / +200 %, G1-F (main) and G1, 2025 and 2026.
- `scripts/g1_maxup_free.py`: reproduces both (`INDEX_STORE=../fo-index-data/data/index`).
Rules: `strategies/S3_G1_put_overnight.md`. The measure is max up after entry, not an exit (the user, 2026-11-06).
