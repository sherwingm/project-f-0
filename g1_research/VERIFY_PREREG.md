# Two verification tests from the public research, pre-registered 2026-11-09 (before any number was computed)

**Why (the user, 9 Nov):** after the Reddit / forum / Zerodha / SEBI research, "do all the verification". Public sources agree that
option buying loses its directional edge to costs, spreads and decay, and nobody has published an after-cost ATM vs ITM test; Zerodha
published one ORB option-buying backtest without its exit rule. Both are checked here on our own data: NIFTY option 1-minute trade
prices (`index_data`, Oct 2024 to Oct 2026). History only, in-sample for G1 (its signals were chosen on this period); nothing live changes.

## Test 1: does an in-the-money strike beat ATM on G1's own signals?
- **Signals:** the 259 G1 history signals (same rule and code path as `scripts/g1_hold_days.py`: first close below the 09:15-09:29 range,
  09:30-13:00, nearest weekly expiry after the day, entry the minute after the signal). G1-F = the subset passing its three filters.
- **Only the strike changes** (`scanner.s3_engine` Leg offset, put strikes): **-1** (one OTM, reference), **0** (ATM, as live),
  **+1** and **+2** (one / two strikes ITM, the main question), **+4** (deep ITM, about delta 0.8-0.9, the "deep ITM" forum idea).
- **Exit:** the live rule: 50 % stop on every minute, else the next session's close (15:29). Same fills, charges and slippage as the
  engine (0.5 % a side, 1 % for 2+ strikes from the money or outside 09:30-15:00); a second run at 2x costs.
- **Measures:** max up first (peak through the next close, no stop: share >= +50 / +100 %, mean, median), then booked: net % of premium
  paid (= return per rupee at risk, since the stop risks a fixed share of the premium), win %, median, total and worst rupees for one lot.
- **Decision rule (fixed):** strike k "beats ATM" only if the paired difference (same days) of net % of premium, k minus ATM, has a mean
  > 0 with paired t >= 2.0, is > 0 in BOTH halves (Oct 2024-Sep 2025, Oct 2025-Oct 2026), and stays > 0 at 2x costs. Judged on G1 (all
  259); G1-F shown alongside. Otherwise: "no evidence that ITM beats ATM here".

## Test 2: replication of Zerodha's ORB on option premium (In The Money, Part 2, Mar 2026)
- **Their rule, as published:** at 09:16 take the CE and the PE whose premium is closest to Rs 200; opening range = that option's own
  09:15-11:15 range; buy when the premium closes above the range high; one CE and one PE trade a day at most; 20 % stop on the entry
  premium; costs + 0.2 % slippage. **Not published: the exit and the expiry.** Fixed here BEFORE any number:
  - expiry = the nearest NIFTY weekly expiry on or after the day (the current week; expiry days included);
  - range = highs of the 1-minute bars 09:15 to 11:14; trigger = the first 1-minute close above it from 11:15 to 15:00; entry = the close
    of the NEXT minute plus slippage;
  - stop = a later 1-minute low <= 80 % of the entry price, filled at 80 % (or at the bar's open if it opened below), minus slippage;
  - exit = the 15:15 minute close minus slippage (an intraday system; 15:25 shown as a check).
  - costs: `server.charges` on both legs; slippage 0.2 % a side (theirs) and 0.5 % (ours) as the stress.
- **Period:** 2024-10-01 to 2026-10-28 (overlaps their Oct 2024-Feb 2026; Mar-Oct 2026 is after their test).
- **Measures:** max up after entry to 15:15 (no stop) first, then win %, mean / median net % of premium, total and per-trade rupees for one
  lot, max drawdown of the one-lot equity in rupees and as % of Rs 1.5 lakh (their capital per lot), by half and by side (CE / PE).
- **Replication verdict:** "matches" if our win rate is within 5 points of their ~48 % and the curve is weak after mid-2024 as they wrote;
  "profitable here" needs mean net > 0 at BOTH slippages and in both halves with t >= 2.

No re-tuning after the numbers. These are tests of public claims, not new strategies; anything that looks good would still need its own
forward paper run before any live use, and only the user decides that.

## Addendum 1 (same day, before any number): the user, "not only ITM vs ATM, the rest too"
**Test 1 also runs on the CALL side** (the G1 mirror, G1-C idea: first close ABOVE the range, ATM call of the nearest weekly after the
day, same exit); call offsets are mirrored (ITM = lower strikes): -1 ITM... i.e. k = +1 OTM, 0 ATM, -1, -2, -4 ITM. This also gives
G1-C's first booked history (only max up was measured before). Same decision rule.

## Test 3: the forum "2 % target / 2 % stop at the open" idea (r/NSEbets, supplied notes; a commenter said it lost every year)
Rs 1 lakh capital, one trade a day: direction = today's open vs the previous close (open above -> buy a call, below -> a put, equal -> no
trade); entry = the 09:29 minute close (+ slippage); strike = 1 strike ITM of the nearest weekly expiry on or after the day; target and
stop = +/- Rs 2,000 on one lot (2 % of capital), checked on 1-minute highs / lows (if both in one minute: the stop counts); otherwise
out at the 09:44 close (a 15-minute hold). Costs: charges + 0.5 % slippage. Verdict: does it lose every year, as claimed?

## Test 4: the 30-minute ORB option-buying bot (r/IndianStreetBets, supplied notes: +Rs 43k before costs, -Rs 1.15 lakh after)
Range = NIFTY 09:15-09:44; signal = the first 1-minute close outside it, 09:45-13:00; buy the ATM option of that side (CE above,
PE below), nearest weekly on or after the day; entry the next minute's close; 30 % premium stop; square-off 15:15. Reported both
GROSS (no charges, no slippage) and NET (charges + 0.5 % slippage), to check the claim that costs flip the sign.

## Test 5: the "11.5-year" risk rules (r/IndiaAlgoTrading, supplied notes: 30 % stop, move the stop after +20 %)
Its entry is not published, so its EXIT rules are tested on our own breakout entries (G1 puts and the call mirror, intraday): stop 30 %
below entry; once the premium has been +20 %, the stop moves up to the entry price and then trails 20 % below the highest premium
seen; else out at 15:15. Compared with the same entries under a plain 30 % stop and under no stop, all to 15:15.

All of tests 3-5 use the same helper (NIFTY option 1-minute trade prices, `server.charges`, one lot by the lot size of the day),
2024-10-01 to 2026-10-28, and report max up first, then win %, mean / median net % of premium, total rupees, worst drawdown, by half
and by year. Forum results are claims to check, not rules we adopt.
