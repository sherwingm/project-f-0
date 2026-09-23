# 07 · The rules that apply to you

Plain-language summary of SEBI's framework for retail participation in algorithmic trading
(circular of 4 February 2025, NSE implementation standards of 5 May 2025, fully applicable to
all brokers from 1 April 2026). This is a summary for orientation, not legal advice; the
circulars are on sebi.gov.in and nseindia.com, and your broker's own terms govern the details.

## What counts as what

- Placing orders through a broker API from your own script is "algorithmic trading" under the
  framework, even when every order is confirmed by hand. That is what this scanner does in live
  mode.
- **Below 10 orders per second per exchange** you are a regular API user: no registration of the
  strategy with the exchange, no Algo ID application by you. This scanner is nowhere near that
  (its own cap is 20 orders per day).
- Self-built strategies may be used for your own account and immediate family (spouse,
  dependent children, dependent parents) — not offered to anyone else.

## What you must actually do

1. **Static IP.** API orders are accepted only from an IP address you have registered with your
   broker. It can be changed at most once per calendar week. Market data reads do not need it.
2. **OAuth and two-factor login.** Groww's TOTP-key flow is exactly this; do not share the secret.
3. **Daily session end.** Access tokens are issued per day; the server logs in again each morning.
4. **Let the broker tag orders.** Every API order carries an exchange identifier added by the
   broker; you do nothing, but it means every order is traceable to you.
5. **Stay under the order-rate threshold.** Keep `MAX_ORDERS_PER_DAY` sensible; never automate
   unattended order bursts.

## The AI reading and SEBI's research-analyst rules

Research-analyst regulations cover recommendations and research reports issued to others. A
personal tool that describes your own data, with no buy/sell/hold recommendation, used only by
you, is outside that regime. Two things would change that: publishing the readings to other
people, or letting the tool recommend. This build blocks the second by design (the model is
instructed not to, and a filter drops any output that does); the first is up to you — keep the
page and the server private.

## Things the scanner deliberately does not do

- No orders without a review screen and a tap; no order triggered by a label.
- No sharing of strategies or signals with anyone.
- No market orders without a price reference; limit orders are the default.
- No intraday polling outside 09:15–15:30 IST, no polling on holidays.
