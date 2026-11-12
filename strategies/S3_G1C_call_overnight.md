# S3 G1-C · NIFTY upside opening-range breakout, call held overnight (pre-registered 2026-11-12, before any G1-C trade)

**Why:** the user, 2026-11-12: "Setup for the call option buying". Paper only, buy only, 1 lot. Nothing here changes G1, G1-F, Near
Tighty, XP, S1 or S2. G1-C has its own ledger (`data/g1c_ledger.json`), its own gate and its own section on the /index page.

**What was seen before this page (disclosed):** the call mirror of G1 has only been run on history, never live.
- `g1_research/VERIFY_RESULT.md` (Test 1, 2024-10 to 2026-10, NIFTY option 1-minute prices, engine fills and charges): 235 call signals, the
  live exit (50 % stop, else the next session's close) lost at EVERY strike: ATM -10.8 % of premium a trade, -Rs 1.6 lakh for 1 lot, win 29 %,
  -12.7 % at double costs; max up through the next close reached +100 % on 20 % of trades (puts: 34 %), mean +65 %, median +35 %.
  ITM calls lost a little less (about +2 to +3 points a trade better than ATM, t below 1: not significant).
- The week of 2-6 Nov 2026 (NIFTY +9 % in six sessions) would have given four up-breaks: -51 % (stopped), +94 %, +362 %, +205 % (open). Four days are
  not evidence; they are why the user wants it running.
So the history is NEGATIVE for this rule; G1-C is a forward paper record to see whether a rising market changes that. It is not an
endorsement, and the live paper result decides, not the four good days.

## Rules (the mirror of G1, no open parameters)
- Signal: NIFTY 1-minute closes. Opening range 09:15-09:29 (high and low). The first 1-minute close OUTSIDE it from 09:30 to 13:00 decides the day:
  above the high = G1-C buys; below the low = no G1-C trade that day (G1 takes it as a put).
- Option: the at-the-money call (strike nearest NIFTY's close of the entry minute, 50-point steps) of the nearest weekly expiry after today.
- Entry: 1 lot (65), at the last ask of the minute after the signal minute (the entry minute); no ask in that minute (older than 60 s) = no trade.
- Exit: stop = the first second the bid is at or below 50 % of the price paid (both days); else sold at the best bid at the first quote of the next
  session's 15:29 minute; a missed close sells at the first bid of the following session.
- No skip filters and no breakout score (both were built and tested for puts only). One position at a time.
- Every trade records max up (the highest bid after entry, % above the price paid) first, then the booked result.

## Gate (judged once, at the 30th trade; the S3 buy gate)
Mean net % of premium > 0, still > 0 at 2x charges, t >= 2, both halves of the 30 trades > 0, worst single loss smaller than the average month.
Report max up first (share >= +50 / +100 %, mean, median), then win %, average, median, total. Passing = "passed its paper gate", nothing more:
no auto-promotion, no real order; only the user decides about money. A failed gate is recorded as failed.

## Pace
About 10 signals a month on the call side in history (235 in 25 months), so the 30th trade is about 3 months out.

## Live paper on the website
`/index`: a G1-C section (today, open position, trades with max up), a Pods row, API `/api/index/g1c`. Alerts say "G1-C".
