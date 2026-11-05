# Pre-registration (written 2026-11-04, before any expiry statistic was computed)

## Chronological split (fixed; never reshuffled)
| Period | Dates | Use |
|---|---|---|
| **Discovery** | 2018-01-01 → 2022-12-31 | look for patterns, build features, fit models |
| **Validation** | 2023-01-01 → 2024-06-30 | check what discovery found; walk-forward inside discovery+validation |
| **Final out-of-sample** | 2024-07-01 → latest stored day | untouched; opened once, by the coordinator, for candidates that passed validation |

The final period holds all the stored option-minute prices (Aug 2024 →), so real option trades are priced only there,
once, for candidates that already passed validation.

Minute-level features exist only from 2021-10, so for them discovery is 2021-10 → 2022-12 (thin); this is reported,
not worked around.

## Decision times (a feature may be used only if published by then)
| Code | Time | Usable inputs |
|---|---|---|
| `T1515` | previous session 15:15 IST | minute bars up to 15:14; daily data of earlier sessions |
| `TCLOSE` | previous session after the official close (≈ 15:30–evening, bhavcopy evening) | that session's full OHLC, VIX close, bhavcopy OI / volume / settle |
| `D-2` | two sessions before the target session, after its close | as TCLOSE, one session earlier |

A `TCLOSE` signal is never filled at that close. Its earliest entry is the next session's open (09:15–09:16 minute)
or a later minute of that session.

## Statistics
- Every rate is reported with its count and a 95 % Wilson interval, and compared with the unconditional rate of the
  same period (two-proportion or binomial test).
- Many hypotheses are tested, so each report keeps a hypothesis log; p-values are corrected with Benjamini-Hochberg
  (FDR 10 %) across that report's family, and the family size is stated.
- Labels: **Observed** (seen, no test), **Suggestive** (discovery effect, BH-significant, not yet validated),
  **Validated** (same sign and a significant effect in validation, then confirmed once in the final period),
  **Rejected**, **Untestable**.
