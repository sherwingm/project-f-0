# Near-expiry signal screen (2026-11-04, test window only, descriptive)

The user: "find the signal" that picks the +100 % near-expiry trades. Code `scanner/near_expiry_signals.py`; workbook `near_expiry_signals_2026-11-04.xlsx`. NIFTY 09:20 buys 0-4 sessions to expiry, entry days 2024-10-01 → 2025-09-30; net of charges, 1 lot; holdout not read.

- **Baseline, calls.** 1796 trades on 243 days; +100 % reached 35%; net -7.3 % sold same day, -5.1 % held to expiry
- **Baseline, puts.** 1796 trades; +100 % reached 42%; net -13.7 % same day, -16.5 % held
- **Answer.** No 09:20 feature picks the +100 % trades. 108 cells: no positive cell reaches t 2 (best Previous day's return, in direction %, high, Call: +68.9 % held, t 1.26). Each positive cell is carried by its 3 best days (for calls, nearly always the 16-17 Apr and 15 May 2025 rallies): without them 24 of 25 turn negative; the one left (puts, spot within 0.9 % of the 20-day EMA, held) is +5 % (sheet Top-day check).
- **What to avoid (strong).** Puts with India VIX at 09:20 high (> 15.03): -66 % held, t -7.4; Puts with 09:20 spot vs 20-day EMA, in direction % high (> 0.92): -53 % held, t -4.3; Puts with Previous 5-day return, in direction % high (> 0.68): -55 % held, t -4.2
- **The one lead.** G1 (downside opening-range breakout put, already pre-registered, forward test from 2026-11-05) earns its money near expiry: trades 1-3 days out +5.6 % (2024-25) and +19.2 % (2025-26) a trade; 4-5 days out +9.4 % then -4.6 %. Not significant (t 0.6 / 1.7) and found after the fact (G1's own sample).
- **Holdout.** Not used. No candidate passed the S3 test gate (t ≥ 2), so nothing opens it.
- **Read with care.** In-sample screen; ~5 of 108 cells reach |t| ≥ 2 by chance. Net of charges, 1 lot.

## G1 by days to expiry (in-sample, G1's own trades)

| Days to expiry | Period | Trades | Mean net | t | Won | Mean without top 3 |
|---|---|---|---|---|---|---|
| 1-3 days | Oct 2024 – Sep 2025 | 82 | +5.6% | 0.61 | 39% | -5.4% |
| 1-3 days | Oct 2025 – Oct 2026 | 79 | +19.2% | 1.72 | 44% | +7.8% |
| 4-5 days | Oct 2024 – Sep 2025 | 46 | +9.4% | 1.23 | 54% | +1.7% |
| 4-5 days | Oct 2025 – Oct 2026 | 52 | -4.6% | -0.67 | 33% | -12.7% |
| 1-3 days | Both | 161 | +12.2% | 1.71 | 42% | +5.2% |
| 4-5 days | Both | 98 | +2.0% | 0.39 | 43% | -2.5% |
