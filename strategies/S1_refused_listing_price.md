# S1 fade · refused sub-₹2 signals: buy anyway if the contract's listing-day price was < ₹10 / < ₹7, v12 exit

**Pre-registered 2026-10-21**, before any number is computed. The user: when a signal is refused only because its
premium is below ₹2 (IRFC 16 Oct, UNIONBANK 21 Oct), buy it on the signal day anyway **if that contract's price on its
first trading day (listing) was below ₹10 (or ₹7)**, and sell it **the same day with the v12 exit**. Replaces the
unrun `S1_refused_buy_first_day.md` design (that one bought on the listing day; the user corrected it). **Nothing live
changes.**

## Trades
- The fade contracts with day-0 option minutes whose realistic entry B (09:16 open + 1 tick) is **below ₹2**: the
  ones the ₹2 floor refuses (`data/results/S1_fade_cheap_dte_trades.csv`, Oct 2024 – Aug 2026). No lot-cost cap, so
  "1 lot too big at the ₹2 floor" cases (like UNIONBANK) are in. Contracts under ₹0.50 at the old opening print are
  missing from the minute sets.
- **Exit:** v12 on 1-minute candles (−20 % stop, trail on at +10 %, 2 % gap, else 15:19), real charges: the
  `v12_net_pct` / `v12_net` columns already computed there (`scanner/fade_cheap_dte.py`).
- **Listing-day price** = the contract's close on its first session with volume > 0, from the NSE bhavcopy cache.

## Groups
All refused; listing price < ₹10; < ₹7; ≥ ₹10 (what the check removes). Per group: N, win %, mean and median net %,
total ₹, date-clustered t, both halves (Oct 2024 – Oct 2025, Nov 2025 – Sep 2026).

## Pass (fixed now), for < ₹10 and for < ₹7
Mean > 0 with t ≥ 2, mean > 0 in both halves. A pass only justifies a paper shadow tag (the user's decision).
