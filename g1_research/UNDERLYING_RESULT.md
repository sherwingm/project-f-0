# G1 follow-through on NIFTY spot, five years: result (2026-11-08). Plan: UNDERLYING_PREREG.md. Script: scripts/g1_underlying.py
Data: NIFTY 1-minute spot from 2021-10-20 (5 years, not 8). 638 G1 downside-breakout signals. Unit = ATR5 (mean daily range of the 5 prior sessions).
F = how far NIFTY kept falling after entry until the next close (spot twin of a put's max up); reach = F >= 1 ATR.

## Q0: does the plain breakout follow through? Barely, and not provably.
| Year | Signals | F (signal) | F (any day, same minute) | N booked-like (signal) |
|---|---|---|---|---|
| 2022 | 140 | 0.92 | 0.83 | +0.08 |
| 2023 | 120 | 0.72 | 0.83 | -0.16 |
| 2024 | 136 | 0.94 | 0.83 | +0.06 |
| 2025 | 124 | 0.84 | 0.83 | +0.18 |
| 2026 | 105 | 0.93 | 0.82 | +0.10 |
| All | 638 | 0.88 | 0.83 | +0.07 |
- F beats the same-minute baseline by +0.056 ATR (t 1.61, p 0.11); the booked-like move by +0.065 ATR (t 1.50, p 0.14). Not significant.
- 33 % of signals fall a full ATR or more after entry (56 % half an ATR, 9 % two ATR). 2023 was negative; 2025 to 2026 positive.
- So the G1 breakout is at most a small directional tilt. Its good option numbers come mostly from a few large moves and the put's convex payoff, not a steady edge in the direction.

## Patterns (40 features, 78 single rules, discovery 248 / validation 127 / confirmation 263)
**0 candidates** (best q = 0.43; bar 0.10). The strongest discovery rules (a down day before: prev-day return, prev 5-day return, yesterday's body) fell to chance in validation (25 % vs 31 %) and in confirmation (42 % vs 35 %, 35 % vs 38 %).
- Instability, not a lead: yesterday's range small (pd_range low) was WORSE in discovery (20 % vs 34 %) and BETTER in validation (37 % vs 23 %) and confirmation (50 % vs 26 %). A sign flip like that means the effect depends on the period, so it is not used.
- Even with five years and 638 signals, nothing in entry-time facts, formation or regime separates big follow-through days.
