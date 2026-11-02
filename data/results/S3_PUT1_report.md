# S3 PUT1 · NIFTY downside first breakout, puts only · spot 2022-01-03 → 2024-09-30

Pre-registered: `strategies/S3_PUT1_downside_breakout_spot.md`. Move = NIFTY's fall from the entry minute's close to the 15:15 close, in %. Hurdle +0.10 % a trade.

## Verdict: **FAIL**

- ✔ at least 150 trades
- ✘ mean ≥ +0.10 %
- ✘ t ≥ 2
- ✘ both halves positive
- ✘ neighbours OR 12 / 18 positive

- Primary: 362 trades, mean -0.006 %, median -0.012 %, t -0.17, fell after entry on 49 % of them.
- Halves: 2022-01-03 → 2023-05-31: +0.014 % (192) / 2023-06-01 → 2024-09-30: -0.028 % (170)

| Cell | Trades | Mean move | Median | t | In direction |
|---|---|---|---|---|---|
| primary (gate) | 362 | -0.006 % | -0.012 % | -0.17 | 49 % |
| OR 12 (gate) | 357 | -0.010 % | -0.011 % | -0.29 | 49 % |
| OR 18 (gate) | 348 | +0.029 % | +0.013 % | 0.87 | 51 % |
| calls, same rules (control) | 302 | +0.053 % | +0.074 % | 1.63 | 57 % |
| puts + P4 filters (trend down, VIX < 14) | 36 | +0.019 % | -0.104 % | 0.21 | 42 % |
| puts, failure exit | 362 | -0.010 % | -0.042 % | -0.85 | 23 % |

| Year | Trades | Mean move | t |
|---|---|---|---|
| 2022 | 140 | +0.017 % | 0.27 |
| 2023 | 120 | -0.058 % | -1.37 |
| 2024 | 102 | +0.024 % | 0.38 |
