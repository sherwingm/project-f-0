# NT · Near Tighty: NIFTY downside opening-range breakout put, only 1-3 sessions to expiry (pre-registered 2026-11-04)

**Why:** the user, 2026-11-04: "keep this as a seperate rule , i will name it as a near tighty dont mix with the nifty
index , i will be a seperate part form it", after the near-expiry studies (`data/results/near_expiry_maxup.md`,
`near_expiry_signals.md`). Near Tighty is its own part of the project, beside S1, S2 and S3: its own page, ledger,
website page and DECISIONS entry. It does not change S1, S2, S3, G1 or `/index`. Buy only, 1 lot, paper only.

**What was seen before this page (disclosed):**
- Near-expiry max up (descriptive): NIFTY 09:20 buys 0-4 sessions out touch +100 % on 30-53 % of trades, but held or
  sold at +100 % they lose on average; no 09:20 feature (108 cells, S3 test window) picks the +100 % trades.
- The lead: G1's own in-sample trades (`data/results/S3_G1_datasheet.csv`, 2024-10 → 2026-10) split by sessions to
  expiry: 1-3 sessions +5.6 % (Oct 2024 – Sep 2025, 82 trades) and +19.2 % (Oct 2025 – Oct 2026, 79) of the premium a
  trade, +12.2 % pooled (161, t 1.71, won 42 %); 4-5 sessions +9.4 % then −4.6 % (98, t 0.39). Found after looking at
  G1's results, so flattered; **the test is forward only.**

## Rules (no open parameters; G1's rules plus one condition)
- **Opening range:** NIFTY 50 high and low of the 1-minute bars 09:15-09:29.
- **Signal:** the first 1-minute close outside the range, 09:30 → 13:00. Trade only when it is below the low; a day
  whose first breakout is upward has no trade. One trade a day.
- **Option:** the at-the-money put (strike nearest NIFTY's close of the entry minute, 50-point steps) of the nearest
  weekly expiry after the signal day.
- **Near-expiry condition (the only difference from G1):** trade only when that expiry is **1, 2 or 3 sessions** after
  the signal day (`server.sessions.sessions_to_expiry`: sessions after the day up to and including expiry, NSE
  holidays counted). 4 or more sessions: no trade that day.
- **Entry:** the minute after the signal minute, at the last ask of that minute.
- **Stop:** sell at the bid when it is ≤ 50 % of the price paid, any second, both days.
- **Exit:** else hold overnight and sell at the last bid of the next session's 09:16 minute. No target.
- No VIX, gap or trend filter (the "avoid" cells of the screen were picked after seeing the data).

## Where it runs
- Paper only on the live server (`server/nt_live.py`), its own ledger `data/nt_ledger.json`, shown on
  the `/index` page (a "Near Tighty · NIFTY" section) and `/api/index/nt`. Nothing is ordered. (Moved onto `/index` on 2026-11-10 at the user's request; it had its own page `/near-tighty` from 2026-11-04 to 2026-11-09.) Prices from the Upstox stream (real bid / ask), charges
  from `server/charges.py`, the lot at entry (65 now). From the first session after it is deployed.
- Overlap with G1: on a 1-3-session day G1 takes the same put; each keeps its own ledger and counts it once.

## Gate, judged at the 30th trade
1. 30 trades. 2. Mean net % of the premium > 0. 3. Still > 0 at 2× charges. 4. t ≥ 2. 5. Both halves positive
(trades 1-15 and 16-30). 6. The worst trade's ₹ loss is smaller than the average month's ₹ result.
About 6-7 trades a month are expected (161 in two years), so 30 take roughly 4-5 months. A fail closes Near Tighty; it
is not rescued by changing the stop, the exit or the 1-3 window.

## After the verdict
- **Pass:** a proposal to the user to consider real orders (Kotak Neo, limit orders, static IP). Nothing is enabled
  automatically.
- **Fail:** closed. The result goes to DECISIONS.md either way.

## SENSEX track (added 2026-11-08, before any SENSEX forward session)
The user, 2026-11-08: "Add sensex" (after `near_tighty_research/reports/NT_SENSEX.md`). Near Tighty on SENSEX is a second,
separate forward test of the same rule. It does not change the NIFTY track, G1 or G1-F.

**Seen before this addendum (disclosed):** the SENSEX history (Oct 2024 → Oct 2026, in-sample, the 1-3 session cut was found
after looking at G1's results): 162 trades sold at the next 09:16 with no target +15.2 % of the premium a trade (t 2.29, median
−16 %, won 44 %, halves +19.0 / +11.9, +₹1.74 lakh at lot 20); max up reaches +100 % on 25 % by the next 09:16, 44 % by the next close.
Oct 2025 → now: 87 trades +11.9 % (t 1.30). Without the 5 best trades +7.8 % (whole history). Not independent of the rule's choice.

**Rules:** identical to the NIFTY track with these substitutions only:
- Spot: BSE SENSEX (`BSE_INDEX|SENSEX`); strike step 100; India VIX as before.
- Option: the at-the-money SENSEX put of the nearest SENSEX weekly expiry after the signal day (contract list: Upstox
  `GET /v2/option/contract`, loaded once a day); traded only when that expiry is 1-3 sessions after the signal day.
- Lot: the contract's lot from that list (20 in the history run).
- Entry, 50 % stop on the bid (any second, both days), exit at the next session's 09:16 bid, no target: unchanged.

**Where it runs:** paper only, the live server, `server/nt_live.py` `NearTightySensexTrader`; own ledger `data/nt_sensex_ledger.json`,
own alerts, own "Near Tighty · SENSEX" section on the `/index` page, API `/api/index/nt_sensex`; `NT_SENSEX_PAPER=true` by default. Nothing is ordered.

**Gate:** the same six checks, on the SENSEX track's own first 30 trades, judged apart from NIFTY (never pooled). A fail closes the
SENSEX track only; it is not rescued by changing the stop, exit, window or lot.

**Known limits (stated now):** the SENSEX range is built from the live stream; a server restart between 09:15 and 13:00 loses that day's
opening range (no trade that day, listed as such); if the contract list cannot be loaded the day is listed as "no SENSEX expiry in the
instrument list: no trade", never filled by guess; the history used a fixed lot of 20 and NSE charge rates.
