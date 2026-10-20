# S1 v11 fade · shadow tag "fd2": puts whose market-hours filing day already fell ≥ 2 % (tag only)

**Pre-registered 2026-10-20**, before any live trade carries the tag. The user's decision: "add it as a shadow tag on
live fade puts only: mark puts whose market-hours filing day already fell 2 % or more; no change to the trades. Review
at 20 tagged trades." **The trades do not change.** Every fade put is still bought and sold by v11.

## Why
`data/results/S1_fade_filing_day_skip.md`: in the v10 backtest, puts whose market-hours filing day already fell
≥ 2 % lost −27.8 % a trade (24 trades, t −3.5, both windows). Under v11's −20 % stop the same trades lost little, so
skipping them would have saved only about ₹2-7k over two years. The tag measures this on live trades.

## The tag (`rule.shadow_fd2` on each fade put)
- **Market-hours filing:** the results filing's NSE time is 09:15–14:50 IST, on the session before day 0 (the
  signal's `filed` date and `filed_time`).
- **D** = the stock's move from the close of the minute before the filing minute to the filing day's 15:29 close,
  minus NIFTY 50's over the same minutes. Kotak 1-minute history, a 5-minute look-back for a missing minute (as in
  the study).
- **Computed by** `scanner/fade_live.py` when it makes the signals (nightly 20:30 IST, again before the open). It is
  stored on the signal as `filing_day = {market_hours, D, D_raw, tagged}`; the live trader copies it to the position.
- **Tagged** = a put with `market_hours` and D ≤ −2 %.
- A put whose D could not be computed (no history, Kotak error) is `unknown`, counted, never tagged.
- Calls get no tag.

## Review at 20 closed tagged puts (real v11 results)
- Report:
  - the tagged puts: N, win rate, mean and median net %, total ₹;
  - the other market-hours puts, and all other puts, the same way;
  - the `unknown` count.
- "Skipping would have helped" only if **both** hold:
  - the tagged puts' total net ₹ < 0;
  - their mean net % is below the other puts' mean.
- If so, the user is asked whether to make it a rule: a new version with its own DECISIONS.md entry. Otherwise the
  tag is dropped. 20 trades is a small sample, so it is a look, not proof.
- The backtest had 24 such puts in 2022-26, about 5 a year, so 20 tagged trades may take several years. The count is
  shown on the Arm F panel.
