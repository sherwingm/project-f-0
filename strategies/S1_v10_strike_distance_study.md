# S1 v10 fade · strike distance study: would a closer strike do better?

**Pre-registered 2026-10-18**, before any of these numbers is computed. Descriptive only: S1 v10 is not changed. A variant
that passes the guard below can only become a new pre-registered paper version (S1 v11), with the user's go-ahead.
Code: `python -m scanner.strike_distance_study` → `data/results/S1_v10_strike_distance.md` / `.xlsx`.

## Why
The fade diagnostics (`strategies/S1_v10_fade_diagnostics.md`) found that among trades where the stock **did** fade, the
losing options had farther strikes (median out of the money: puts 7.0 % vs 5.4 % for winners, calls 8.0 % vs 5.6 %).
The user chose to test closer strikes. **Already seen (disclosed):** in that study's plain bucket comparison, puts more than
5 % out of the money averaged +5.6 % / +17.2 % of premium against −3.3 % / −7.6 % for those under 2 % (2022-24 / 2025-26),
and no strike-distance bucket passed the guard on option net %. That comparison mixes different stocks (the distance is set
by the stock's price and lot size); this study holds the signal fixed and changes only the strike.

## Signals and the baseline
The same signals, expiry choice, entry (day-0 open + 1 tick; VWAP + 1 tick as the realism check), same-day exit (15:20,
close − 1 tick), charges and slippage as `scanner/backtest_s1_v10.py`, in both windows: 2022-24 (2022-01-01 → 2024-12-31)
and 2025-26 (2025-01-01 → 2026-09-25). Event store with filing times through `EVENTS_DB` (the seeded store). The
baseline is v10's walk: from the strike nearest the previous close, away from the money, at most 15 strikes, the first
with ≥ 50 contracts, a fill ≥ ₹2 and one lot within ₹600-8,000.

## Variants (fixed now)
1. **Cap 3 %** and **Cap 5 %** (keeps the ₹600-8,000 budget): v10's walk, but it stops at the last strike within 3 % (5 %)
   out of the money of the previous close; no strike within the cap that fits → no trade.
2. **One step closer** (may break the ₹8,000 ceiling): the strike one listed step nearer the money than the baseline pick,
   if it has ≥ 50 contracts and a fill ≥ ₹2; if the baseline is already the start strike, the same trade.
3. **At the money** (may break the ceiling): the start strike itself (nearest the previous close); if it fails the
   liquidity test, the next strike out of the money that passes (at most 2 steps). No lower or upper cost limit.

Variants 2 and 3 break the user's ₹600-8,000 rule, so they answer "what would the strike itself do", and the report
shows the lot cost they need. Only a variant inside the budget (1) could become a rule as it stands.

## Outcomes and tables (per window, per side PE / CE and both)
- Trades, mean and median net % of premium, hit rate, mean net ₹ per trade, total net ₹, mean lot cost, median % out of
  the money, date-clustered t; with the open entry and the VWAP entry.
- **Paired:** on the signals traded by both the baseline and the variant, the per-signal difference in net % and in net ₹
  (variant − baseline), with its date-clustered t.
- For the caps: what the dropped trades had earned in the baseline.

## The guard (decides "better")
A variant is **better** only if, on the paired signals, its mean net % **and** its mean net ₹ beat the baseline in **both**
windows, with **both** entries (open and VWAP), the pooled t of the net-% difference ((t₁ + t₂) ÷ √2) is ≥ 2, and the
open-entry t is ≥ 1 in each window. 4 variants × 2 outcomes are reported; with that many, one may pass by chance. A cap
also has to show that the trades it drops lost money in both windows.

## Verification
Before the answer goes to the user, the headline numbers are re-checked by independent code (or agents if the user asks),
including a rebuild of about 10 trades per variant from the bhavcopy price files.

## Known limits
- Not out of sample (both windows were used by S1 v2-v10 and the diagnostics).
- The open print is optimistic, more so for less-traded strikes; the VWAP entry is the check.
- Daily data only: no intraday path.
