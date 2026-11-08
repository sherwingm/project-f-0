# Near-expiry research: the search for the max up (its own part)

The user, 2026-11-08: "from our finding for the other chat, which method gets good result, and keep this as another
part of search for the max". This folder is the near-expiry option-buying search that grew out of the question "capture
trades of +100 % or more near expiry". It is separate from `near_tighty_research/` (Near Tighty only),
`expiry_research/` (the independent expiry study) and `g1_research/` (the index chat's G1 / G1-F work). Nothing here
changes a live rule.

**Measure (the user's default):** results lead with max up after entry (share reaching +50 / +100 / +200 %, mean, median),
then the booked result.

| Path | What |
|---|---|
| `FINDINGS.md` | which method gets a good result, which do not, what is still open (read this first) |
| `results/method_scoreboard.csv` | one row per method: sample, max up, booked result, t, verdict, source file |

## Where the underlying files live (not moved)
- Near-expiry buying by days to expiry, NIFTY 1-minute and stock options: `data/results/near_expiry_maxup.md`, `near_expiry_*.csv`, `near_expiry_maxup_2026-11-04.xlsx`, `scanner/near_expiry_maxup.py`.
- 09:20 entry-feature screen: `data/results/near_expiry_signals.md`, `scanner/near_expiry_signals.py`.
- Expiry-day blasts (2x to 20x, rupee results): `data/results/expiry_blasts.md`, `expiry_blasts_2026-11-05.xlsx`, `scanner/expiry_blasts.py`.
- N1 (expiry-day breakout): `strategies/S3_N1_near_expiry_orb.md`, `data/results/S3_N1_history.md`, `scanner/s3_n1.py`.
- Near Tighty: `near_tighty_research/`, `strategies/NT_near_tighty.md`.
- G1 / G1-F, SENSEX, call mirror: `g1_research/`, `strategies/S3_G1_put_overnight.md`.
- Independent expiry study: `expiry_research/reports/FINAL_RESEARCH_REPORT.md`.

The index chat keeps its own scope (G1 / G1-F, no near-expiry rule); this part is read only when the user asks.
