# Evidence Review: OI/PCR Buildup Signals, Paper-Trading Realism, and Retail F&O Risk Rules for NSE Single-Stock Derivatives

## TL;DR

- **Directional prediction from OI/PCR is weak-to-absent on single stocks.** The best Indian evidence (a 2020 NSE study published in the *IIMB Management Review*) found that put-call ratios carried some directional information at the **index** level around a 0.83 threshold and that open-interest changes had some explanatory power for next-day index returns, but that the PCR built from implied volatility predicted **volatility, not direction**. At the single-stock level, where one large trade can double a contract's OI, no peer-reviewed study was found that validates the "long buildup / short buildup" classification at daily resolution.

- **Paper-trading self-scoring overstates accuracy unless you fix the cause.** In a documented paper-trading contest, simulated trades returned +0.23% while the same participants' live trades lost 1.3% on average. The two drivers are fills at displayed prices that a live order would not get, and the trader scoring "did I guess what the rule would say" rather than "was the rule right".

- **Realistic fills are the difference between a paper account and a fantasy.** For illiquid stock options the honest model is mid ± half-spread ± a market-impact penalty proportional to your size against visible depth. One lot against five lots of visible depth costs the spread; five lots against one lot of depth costs several spreads.

- **Transaction costs after April 2026 are a first-order factor.** Futures STT 0.05% on sell; options STT 0.15% of premium on sell (0.15% of intrinsic value if exercised); NSE exchange charges roughly 0.00345% on futures turnover and 0.053% on options premium; SEBI ₹10 per crore; stamp duty 0.002% futures / 0.003% options on the buy side; 18% GST on brokerage plus exchange and SEBI charges; physically settled stock derivatives attract delivery STT of 0.1% on both sides.

- **Retail risk rules are mostly folklore, with three exceptions:** a hard daily-loss halt, fixed-fraction (or fractional-Kelly) position sizing, and a portfolio-level margin cap. "Never risk more than 2% per trade" is harmless but not evidence-derived.

- **SEBI's base rate (FY22–FY24 study):** about 93% of individual F&O traders lost money; net losses of ₹75,000 crore in FY24 alone. This is the null hypothesis a paper account must beat.

## 1. Empirical evidence on OI/PCR/buildup signals

**PCR on Indian markets.** The 2020 NSE study tested put-call ratios, volume put-call ratios and open interest. Findings: a PCR above roughly 0.83 preceded weaker index returns and below it stronger ones, with only OI showing significant explanatory power for returns; the implied-volatility PCR had no directional power but was a significant explanatory variable for subsequent volatility. Treat the 0.83 threshold as illustrative and index-level, not as a parameter.

**International context.** Pan and Poteshman (2006) found that put-call volume ratios built from *newly opened* positions predicted next-day US stock returns, with the effect concentrated in trades by informed clients and decaying within days. Studies that use aggregate PCR (all trades, all clients) find much weaker effects. The scanner's PCR is an aggregate open-interest ratio, the weaker construction.

**OI-based buildup labels.** "Price up with rising OI" is by definition a description of what has happened. A statistically rigorous daily-resolution test of whether that label predicts the next sessions' return on NSE single stocks does not exist in the literature reviewed. Index-level OI changes show modest explanatory power; single-stock OI is far noisier.

**Implication for the scoreboard.** Expect the system's Bullish/Bearish label to score close to a random three-way split (33–40%) against a 3-session move. Your own calls can exceed that only by adding information the numbers don't contain (results, orders, sector moves, catalysts), which is what the evidence-verdict feature is for.

## 2. Why paper-trading self-scoring overstates accuracy

**Post-decision bias and the money-at-risk effect.** With nothing changed but real money, results deteriorate: paper +0.23% vs live −1.3% in the contest study. Part of that is behaviour under risk; part is fills.

**Instant fills at displayed prices.** Paper platforms fill at the screen price; live orders in thin contracts don't. Fill quality alone can flip a strategy's sign.

**Fix.** Score calls and labels against a *realistic-fill outcome* (what you would have made after spread and impact), record calls before seeing the label (already built), and keep the same horizon and threshold across every call so the numbers are comparable.

## 3. Realistic fill and slippage model for illiquid NSE stock options

Never assume a fill at last-traded price. Recommended model:

```
buy_fill  = min(best_ask, mid + half_spread + impact(q))
sell_fill = max(best_bid, mid − half_spread − impact(q))
impact(q) = max(0, (q − visible_qty_at_best) / visible_qty_at_best) × half_spread × κ
```

κ starts at 1.0 and is calibrated against fills you actually observe. Upstox's full quote exposes five levels of depth, enough for this.

**Fallback when depth is unavailable:** LTP ± 0.5% for liquid single-stock futures; LTP ± 3% for out-of-the-money options with OI under 500 contracts; refuse the fill for contracts with OI under 100.

**Latency slippage:** add half a tick in the direction of your order for the 100–500 ms between seeing a price and hitting the exchange.

## 4. Transaction-cost model (post-April-2026)

| Component | Futures | Options |
|---|---|---|
| Brokerage | ₹20 per order flat (discount brokers) | ₹20 per order flat |
| STT (sell side) | 0.05% of contract value | 0.15% of premium; 0.15% of intrinsic value if exercised |
| NSE transaction charges | ~0.00345% of turnover | ~0.053% of premium |
| SEBI fee | ₹10 per crore | ₹10 per crore |
| Stamp duty (buy side) | 0.002% | 0.003% |
| GST | 18% of (brokerage + exchange + SEBI) | same |
| Physical settlement at expiry | delivery STT 0.1% both sides | same |

Illustrative single-lot round trip on a ₹1,000 stock future, lot 500 (contract value ₹5,00,000): STT ₹250, exchange ₹34, stamp ₹10, SEBI ₹1, brokerage ₹40, GST ₹13.5 → about **₹350** in charges. With 0.5% slippage each side that becomes about ₹5,350: **slippage, not fees, is the dominant cost**. Exchange rates change; verify per-lakh figures against NSE circulars before hard-coding.

## 5. Retail F&O risk rules: what the evidence supports

| Rule | Evidence | Recommendation |
|---|---|---|
| Hard daily-loss halt (e.g. stop at −3% of capital) | Strong: drawdown-triggered halts are the primary control on regulated prop desks | Server-side kill switch: block new orders once the day's P&L ≤ −X% of paper capital |
| Fixed-fraction / fractional-Kelly sizing | Strong: Kelly optimality is proven; half- to quarter-Kelly keeps most growth at far lower variance | Cap lots by capital, not conviction |
| Portfolio margin cap | Moderate: e.g. total margin ≤ 50% of capital | Hard cap on the sum of margin across open positions |
| "Never risk more than 2% per trade" | Weak: heuristic, not derived | Harmless default, not a substitute for the above |
| Greeks-based limits | Weak for retail single-leg books | Skip until multi-leg |
| No new option opens on expiry day | Moderate: gamma and pin risk are well documented | Block option opens on expiry day; futures fine |

## Recommended architecture for the paper account

1. **Fill engine** — best bid/ask from the live quote, mid ± spread ± impact; liquidity-tier fallback when depth is missing; refuse fills on contracts with OI < 100.
2. **Cost engine** — book every simulated fill with the full charge stack; use Upstox's Brokerage Details API (`GET /v2/charges/brokerage`, in the read-only token's scope) when available.
3. **Margin** — real SPAN + exposure via `POST /v2/charges/margin` on the Review screen; enforce a portfolio margin cap.
4. **Kill switch** — mark positions to live LTP every poll; block new paper orders once the day's paper P&L crosses the limit.
5. **Scoreboard** — score labels and calls against realistic-fill returns over the horizon, not raw close-to-close.

## Caveats

- Exchange transaction-charge rates are revised periodically; verify before hard-coding.
- The 0.83 PCR threshold is index-level and dated.
- No study validates the long/short-buildup label on NSE single stocks at daily resolution; the scoreboard is the experiment.
- Depth-based fills need Level 2 data; Upstox's full quote provides five levels.
