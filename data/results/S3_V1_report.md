# S3 V1 · buy the NIFTY ATM straddle when options are cheap · 2025-10-01 → 2026-10-30

Pre-registered: `strategies/S3_V1_cheap_straddle.md`. Held to the expiry day's 15:15. Net after slippage and charges, % of the premium.

## Claim 1, cheap straddles make money: **FAIL**

- ✘ at least 60 trades
- ✘ mean > 0
- ✘ t over expiries ≥ 2
- ✘ both halves positive
- ✘ at 2× costs mean > 0
- ✘ neighbours positive

- t over expiries -0.74 (22 expiries); halves -20.7 % (20) / -4.6 % (31); 2× costs -13.1 %

## Claim 2, expensive straddles (ratio10 ≥ 1.1, 14:45) lose: **NOT CONFIRMED**
- 172 trades, -9.0 %, t over expiries -1.41 (needs ≥ 30 trades, mean < 0, t ≤ −2)

| Group | Trades | Mean net | Median | t | Won | Max up mean | Max up median | ≥ +50 % | ≥ +100 % | Total ₹ |
|---|---|---|---|---|---|---|---|---|---|---|
| primary: entry 14:45 · ratio10 < 1.0 | 51 | -10.9 % | -27.8 % | -1.14 | 39 % | +50 % | +23 % | 37 % | 20 % | -89,635 |
| neighbour: entry 14:45 · ratio10 < 0.9 | 28 | -15.4 % | -29.7 % | -1.65 | 32 % | +40 % | +21 % | 29 % | 14 % | -85,581 |
| neighbour: entry 14:45 · ratio10 < 1.1 | 87 | -14.5 % | -31.5 % | -2.16 | 34 % | +44 % | +23 % | 36 % | 15 % | -194,414 |
| neighbour: entry 14:45 · ratio5 < 1.0 | 44 | -9.9 % | -29.7 % | -0.88 | 36 % | +54 % | +34 % | 41 % | 23 % | -96,708 |
| neighbour: entry 09:45 · ratio10 < 1.0 | 68 | -4.7 % | -17.0 % | -0.59 | 35 % | +53 % | +23 % | 41 % | 18 % | -69,788 |
| expensive: entry 14:45 · ratio10 ≥ 1.1 | 172 | -9.0 % | -24.7 % | -1.78 | 36 % | +50 % | +31 % | 33 % | 14 % | -404,971 |
| every 14:45 day | 259 | -10.8 % | -25.9 % | -2.68 | 36 % | +48 % | +28 % | 34 % | 14 % | -599,385 |

Primary by days to expiry at entry (max up while held):

| Group | Trades | Mean net | Median | t | Won | Max up mean | Max up median | ≥ +50 % | ≥ +100 % | Total ₹ |
|---|---|---|---|---|---|---|---|---|---|---|
| DTE 1.0 | 12 | -29.5 % | -45.4 % | -1.63 | 25 % | +23 % | +4 % | 17 % | 8 % | -44,248 |
| DTE 2.0 | 9 | -16.1 % | -8.9 % | -1.18 | 44 % | +34 % | +23 % | 33 % | 11 % | -31,374 |
| DTE 3.0 | 9 | -24.5 % | -0.4 % | -1.61 | 44 % | +40 % | +43 % | 44 % | 0 % | -44,421 |
| DTE 4+ | 21 | +7.7 % | -7.2 % | 0.41 | 43 % | +76 % | +39 % | 48 % | 38 % | 30,407 |

Skipped: 12 ({'no IV': 10, 'no expiry': 2})
