# S3 B1 · NIFTY opening-range breakout confirmed by option volume, long ATM option

Pre-registered 2026-10-30, **before any B1 option return was computed**. Buy only. Rules: DECISIONS.md "S3 · index
options" and "S3 · buy-only, tested on 2024 → today". Engine: `scanner/s3_engine.py`; runner `scanner/s3_buy4.py`.
Idea (the user, 2026-10-30): buy a call (or put) when NIFTY breaks out of its morning range with high volume, exit the
same day.

**Not independent of P4.** P4 (closed, 2026-10-23) tested the opening-range breakout with VIX < 14 and trend filters
on 2024-10 → 2025-09 (−3.6 % a trade; no filter −3.3 %). B1 replaces those filters with a volume confirmation and
runs on the whole window. The first half overlaps P4's test window.

## Window
2024-10-01 → 2026-10-28. Halves: 2024-10-01 → 2025-09-30 and 2025-10-01 → 2026-10-28.

## Signal on session d
- **Opening range:** NIFTY 50 spot high and low of the 1-minute bars 09:15-09:29 (**15 minutes**).
- **Breakout minute:** a 1-minute spot close above the range high (→ call) or below the range low (→ put), between the
  end of the range and 13:00.
- **Volume confirmation:** the index has no volume, so the option's is used. At the breakout minute, take the option
  that would be bought: the ATM strike (nearest that minute's spot close) and side, of the expiry below. Its volume in
  that minute must be **at least 2×** the median of its per-minute volume over the 30 minutes before (minutes with no
  row count as 0), and above 0.
- The **first confirmed** breakout minute of the day is the signal. A breakout minute without the volume is skipped and
  the scan goes on. One trade a day at most.

## Trade (primary)
- **Entry:** the minute after the signal minute. Buy 1 lot of that ATM option.
- **Expiry:** the nearest weekly expiry with at least one session left after d (on an expiry day, the next one), as P4.
- **Exit**, the first of: stop at −**25 %** of the premium paid; trailing stop 25 % below the highest value since
  entry (once in profit); time 15:15.
- Costs and lot as in every S3 pod.

## Gate (unchanged S3 gate)
At least 30 trades; net mean % of the premium paid > 0 and > 0 at 2× costs; t ≥ 2; positive in each half; worst trade
smaller than the average month (₹); neighbours net positive.

**Neighbours (fixed):** opening range 12 and 18 minutes; volume 1.6× and 2.4×; stop 20 % and 30 %.

## Also reported (no effect on the verdict)
- **Baseline:** the first breakout of the day with no volume confirmation (same entry, expiry and exits).
- Calls vs puts; exits by reason; every trade.

## Look-ahead
The range, the breakout and the volume use bars up to the signal minute; the fill is the next minute's close. No
parameter is picked from B1's results.
