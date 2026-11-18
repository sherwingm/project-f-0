# G1-F excursion audit, time-stop and inverse-volatility sizing: results (18 Nov 2026)

Plan: `PREREG_V3_EXIT_SIZING.md` (commit 46120f9e8, before any number). Script `scripts/v3_exit_sizing_opt.py`; raw output `results/v3_run_output.txt`; tables `results/v3_year1_grid.csv`, `v3_selected_comparison.csv`, per-trade paths `v3_year1_paths_*.csv`. Tighter stops and trailing locks were NOT run (already tested earlier, user chose option 1). All entries kept. Engine baseline vs recorded net %: max difference 0.26 points. Needs `INDEX_STORE=C:/Users/sherw/fo-index-data/data/index`.

## Year-1 audit (G1-F, 75 trades: 35 winners, 40 losers, 29 stops)
- MAE (lowest option close before exit): winners median -20 % (p10 -41); losers median -51 %. A level of -41 % spares 90 % of winners and catches 85 % of losers, but the live 50 % stop already acts there; descriptive only.
- MFE: winners median peak +149 %; 56 % of all trades peaked above +50 %, 43 % above +100 % (of those, realised median +93 %). Giveback (peak minus realised, points): winners median 39; losers median 66 (mean 91). Losers often had a peak and gave it back.
- Time to +20 %: 100 % of winners reached it (median 79 min); 48 % of losers reached it (median 34 min). Time to +50 %: 89 % of winners (median 347 min, i.e. overnight); 28 % of losers (median 77 min).

## Year-1 grid (G1-F; G1 outside G1-F in the gate)
- Baseline G1-F: win 46.7 %, mean +25.3 %, PF 2.21, Sharpe 2.19, max drawdown Rs -34.9k.
- Time-stops: T30 g0: Sharpe 2.82, PF 3.90, drawdown -15k (fires on 40 of 75 trades); longer N and the +10 % bar are worse; T240 below baseline.
- Sizing: VIX 13 / 15: Sharpe unchanged 2.19; ATM-IV 14: Sharpe 2.25, PF 2.29, mean +27.7 %.
- G1 outside G1-F (53 trades): baseline PF 0.40, Sharpe -2.84; T30 g0 Sharpe +0.18; IV-14 sizing Sharpe -2.10.
- Pre-registered gate (Sharpe and PF up on both, mean not lower): passers T30_0 and S_iv14. Rule: fewest parameters first, so **S_iv14 was chosen**.

## Year 2, opened once for S_iv14 (baseline vs optimised)
- G1-F Year 2 (79 trades): win 35.4 %; mean +14.4 % vs +13.6 %; PF 1.57 vs 1.51; Sharpe 1.37 vs 1.27; max drawdown -41.6k vs -54.7k; total Rs +84.3k vs +96.7k.
- G1 outside G1-F Year 2 (52): Sharpe -1.64 vs -1.89; PF 0.57 vs 0.54.
- **Result: the chosen rule does not hold out of sample** (Sharpe, PF and drawdown all worse on G1-F; Sharpe and PF worse on the siblings). Year-1 gain was +0.06 Sharpe, inside noise.

## Honest reading
- No improvement is established. The Year-1 sizing gain was tiny, did not repeat, and fractional lots are a simplification.
- T30_0 (exit unprofitable trades after 30 minutes) also passed the Year-1 gate and looks large (G1 outside G1-F from Rs -105k to +5k). Per the rule it was not chosen and **Year 2 was not opened for it**; opening it now would be a second look at Year 2 and needs your decision. Its caveats: it fires on 40 of 75 trades, it exits many trades that later become overnight winners in Year 2 (winners need a median 347 min to +50 %), Year 1 is the weakest-regime sibling sample, and it is a stop-type rule of the kind earlier studies found to lose.
- The 8 best trades are 77 % of the rupees; any exit rule is judged mostly on whether it clips them.
