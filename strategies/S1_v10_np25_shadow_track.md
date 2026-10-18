# S1 v10 fade · shadow track "puts only above NP YoY 25 %" (live paper)

**Pre-registered 2026-10-18** at the user's request ("track profit growth above 25 % on live paper alongside v10"),
before any trade is judged under it. Paper only; **S1 v10 itself is not changed**: every v10 fade trade is still taken.

## Why
The fade diagnostics (`strategies/S1_v10_fade_diagnostics.md`) found that puts whose net profit grew only 10-25 % YoY
did worse in both backtest windows (−12 % / −8 % a trade vs +11 % / +16 % above 25 %), but the lead failed with the
realistic VWAP entry in 2025-26 and is no better than chance across ~105 measures tested before entry. Old data cannot
settle it; new live trades can.

## The shadow rule (fixed now)
- **In the shadow track:** every v10 **call**, and every v10 **put whose net profit YoY at the filing is above +25 %**.
- **Left out by it:** v10 puts with net profit YoY of +10 % to +25 % (the band v10 trades and the shadow would skip).
- It is a strict subset of v10, so no extra order is placed: each live fade position is **tagged** at entry with its
  numbers (`np_yoy`, `np_qoq`, `rev_yoy`) and `shadow_np25` (true / false). Trades made before the tag existed (15-16
  Oct 2026) are classified from the numbers already in their `why` note, the same filing numbers v10 used.
- The paper summary (`/api/paper/summary` → `fade_split`) shows, for v10 all / the shadow track / the left-out puts: closed
  trades, wins, total net ₹, mean net % of premium, and the open positions' unrealised ₹.

## How it is judged (fixed now)
Descriptive until **at least 40 left-out puts** have closed (about one results season or more). Then the comparison is the
mean net % of premium of the left-out puts against the shadow track's, with a date-clustered t. The shadow can only
become a rule (a new pre-registered S1 v11) if the left-out puts lose money **and** do worse than the shadow track with
|t| ≥ 2, and the user agrees. Fewer than 40 by the end of the paper run: reported as too few, no conclusion.

## Known limits
- Small samples for months; one results season is heavily clustered on a few days.
- The live entry is the ask after 09:15 (not the backtest's open), which is exactly what this track measures.
