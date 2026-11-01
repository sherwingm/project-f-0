# S3 B2 stage A · NIFTY 50 spot, 2022-01-03 → 2024-09-30 (the window the idea has not seen)

Pre-registered: `strategies/S3_B2_accepted_breakout.md`. Spot only: the move of NIFTY in the trade's direction from the entry minute's close to the exit minute's close (the minute after the first close back inside the range, else 15:15). Hurdle +0.10 % a trade (costs and decay of the option, from B1's trades).

## Verdict: **FAIL**

- ✔ at least 150 trades
- ✘ mean ≥ +0.10 %
- ✘ t ≥ 2
- ✔ each half positive
- ✔ acceptance 10 and 20 neighbours positive

- Trades 595 of 595 signal days; mean +0.019 %, median -0.081 %, t 1.26; in the direction 28 %.
- Halves: 2022-01-03 → 2023-05-31: +0.032 % (317) / 2023-06-01 → 2024-09-30: +0.004 % (278)

| Cell | Trades | Mean move | t | In direction |
|---|---|---|---|---|
| OR 15 min · accept 15 closes · stop 25 % | 595 | +0.019 % | 1.26 | 28 % |
| OR 15 min · accept 10 closes · stop 25 % | 612 | +0.024 % | 1.62 | 26 % |
| OR 15 min · accept 20 closes · stop 25 % | 576 | +0.020 % | 1.31 | 29 % |
| first breakout, no acceptance (B1's signal), same exits | 664 | +0.003 % | 0.29 | 26 % |

| Group | Trades | Mean move | t |
|---|---|---|---|
| CE | 289 | +0.017 % | 0.88 |
| PE | 306 | +0.020 % | 0.91 |
| fail | 434 | -0.143 % | -27.08 |
| time | 161 | +0.454 % | 12.79 |
| 2022 | 225 | +0.042 % | 1.43 |
| 2023 | 212 | -0.016 % | -0.95 |
| 2024 | 158 | +0.034 % | 1.11 |
