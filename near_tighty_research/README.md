# Near Tighty research (its own storage; not mixed with expiry_research/ or the index / NIFTY work)

The user, 2026-11-04 and 2026-11-06: Near Tighty is its own part of the project; its optimisation is totally different
from the overall index / NIFTY optimisation. Anything related to Near Tighty is stored here.

**Rule of the part:** NT = G1's NIFTY downside opening-range-breakout put, only when the expiry is 1-3 sessions away
(`strategies/NT_near_tighty.md`). Our measure is the **max up after entry**, not an exit or booked profit.

| Path | What |
|---|---|
| `data/nt_maxup_trades.csv` | storage file: every G1 history trade (Oct 2024 → Oct 2026) with its max up after entry in four windows, no stop or exit applied; `nt = 1` for 1-3 sessions to expiry |
| `results/nt_maxup_summary.csv` | the same by days to expiry, NT vs not NT, and the two halves |
| `reports/NT_MAXUP.md` | the plain-English result |
| `scripts/nt_maxup.py` | reproduces both files (`INDEX_STORE=../fo-index-data/data/index`) |
| `reports/NT_TARGETS.md` | which sell-at level (1.5x-10x) books the best result, NT, history (2026-11-07) |
| `data/nt_target_trades.csv`, `results/nt_target_summary.csv` | per trade and per level / window: sold price, reason, net, max up |
| `scripts/nt_targets.py` | reproduces both |

## Related Near Tighty files that live elsewhere (not moved)
- `strategies/NT_near_tighty.md`: the pre-registered rules and gate.
- `server/nt_live.py`, `server/nt_pages.py`, `templates/near_tighty.html`, `tests/test_nt_live.py`: the live paper run.
- `data/nt_ledger.json` (on the live server): the live paper ledger. Live trades record `max_bid` and `max_up_pct`.
- `data/results/near_expiry_maxup.md`, `near_expiry_signals.md` and their csv / xlsx: the near-expiry studies that led to it.
- `data/results/S3_G1_datasheet.csv`: the G1 trades NT is cut from.

Later Near Tighty work (live-trade max up, optimisation, studies) goes in this folder.

**Reporting default (the user, 2026-11-07):** results lead with max up after entry (share reaching +50 / +100 / +200 %, mean, median), then the booked result.
