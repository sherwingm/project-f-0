# Data dictionary: anatomy_dataset.csv (G1-F, 154 trades); same columns in anatomy_dataset_G1.csv (259 puts) and anatomy_dataset_G1C.csv (235 calls)

Labels: PRE = known before the entry minute. POST = known only after entry (explanation only, never a predictor). OUT = the recorded outcome.
Recorded source rows: `g1_research/results/g1_live_replay_trades.csv` (G1 / G1-F) and `g1_research/data/g1c_opt_trades.csv` column B (G1-C), joined to `index_context_research/results/context_dataset.csv` for entry time, expiry and the feature columns marked "ctx". Trade = ATM option bought the minute after the signal minute, 50 % stop, otherwise exit at the next session's 15:29 close.

| column | label | meaning |
|---|---|---|
| tset, side | PRE | trade set (G1F / G1 / G1C); PE (put) or CE (call) |
| day, weekday_name, quarter, half | PRE | entry date, weekday, quarter of entry day (ctx), D / V / L period flag (ctx) |
| entry_time | PRE | entry minute (signal minute + 1), ctx |
| expiry | PRE | expiry of the contract (ctx) |
| ret1_pct, ret5_pct, ret10_pct, ret20_pct | PRE | NIFTY previous close vs the close 1 / 5 / 10 / 20 sessions earlier (daily closes = last spot minute bar), % |
| prev_vs_sma20_pct, prev_vs_sma50_pct | PRE | previous close vs the mean of the last 20 / 50 closes (up to the previous close), % |
| ma_structure | PRE | bull = close > SMA20 > SMA50; bear = close < SMA20 < SMA50; else mixed |
| vix_signal | PRE | India VIX close of the last minute at or before the signal minute (`index_data.load.vix_1m`, repaired series) |
| vix_prev_close | PRE | VIX previous session close |
| vix_chg5_pct, vix_chg1_pct | PRE | VIX previous close vs 5 / 1 sessions earlier, % |
| vix_signal_vs_prev_pct | PRE | VIX at the signal minute vs previous close, % (sudden expansion measure) |
| gap_pct_open | PRE | 09:15 open vs previous close, % |
| signal_close | PRE | NIFTY close of the signal minute |
| intraday_ret_to_signal_pct | PRE | signal-minute close vs the 09:15 open, % |
| or_width_pct | PRE | 09:15-09:29 range high / low - 1, % |
| beyond_or_pct | PRE | distance of the signal close beyond the opening range edge in the trade direction (puts: below the range low), % of the edge |
| breakout_min_after_0930 | PRE | minutes from 09:30 to the signal minute |
| dte_calendar, dte_sessions | PRE | calendar days / sessions after the entry day up to expiry |
| breadth_prev, atm_iv, iv_skew, pcr_oi, gift_basis, us_prev_ret, fut_oi_chg, fut_px_chg, fii_fut_longshare, event_window, expiry_day | PRE | copied from context_dataset.csv. breadth_prev = survivorship-biased proxy (share of current constituents up on the previous day); gift_basis is a daily settlement proxy, not the pre-open level; atm_iv Black-Scholes from last-trade prices. Missing stays missing |
| net_pct | OUT | recorded net % = net rupees after slippage and charges / premium paid in rupees (engine `net_pct_premium`) |
| net_rs | OUT | recorded net rupees |
| maxup_pct_next_close_file | OUT/POST | recorded max up: highest option value after entry through the next close, % above price paid (no stop applied) |
| exit_reason_file | OUT | recorded exit reason: stop / time (= next session 15:29) |
| engine_net_pct, engine_net_rs, engine_reason, repro_diff_pct, repro_status | check | engine re-run of the same ATM option, 50 % stop, exit next 15:29 (consistency check only); repro_diff_pct = engine - recorded |
| strike, paid_price, premium_rs, fees_rs_engine | PRE (strike, paid_price, premium_rs) | contract strike; price paid per unit incl. slippage; premium paid in rupees (lot included); engine fees |
| mfe_any_pct, peak_at | POST | highest option minute close vs price paid through the next close (equals the file's max up within 0.005) and its time |
| peak_on_entry_day, peak_trading_min_after_entry | POST | whether the peak fell on the entry day; trading minutes from entry to the peak (375 trading minutes a session) |
| mfe_held_pct | POST | same but only while the position was held (to the exit minute) |
| mae_held_pct | POST | lowest option minute close between entry and exit as % vs price paid (negative = below); MAE |
| mae_any_pct, mae_before_peak_pct | POST | lowest value through the next close regardless of the stop; lowest value before the peak |
| exit_day, exit_time, exit_reason | POST | engine exit (identical to the file in all trades) |
| duration_trading_min, duration_wall_min | POST | trading minutes / wall-clock minutes from entry to exit |
| post_next_open_gap_pct | POST | next session open vs entry-day close, % |
| post_next_close_vs_entrydayclose_pct | POST | next session close vs entry-day close, % |
| post_entryday_close_vs_signalclose_pct | POST | entry-day close vs signal-minute close, % |
| post_spot_move_signal_to_nextclose_pct | POST | next session close vs signal-minute close, % |
| stop_after_max_up_pct, stop_nextclose_vs_paid_pct | POST | for stopped trades only: highest option value after the stop minute, and its value at the next close, both vs price paid |
| ret1_class .. ret20_class | PRE | quintile 1-5 (1 = lowest return) using the edges in class_boundaries.csv |
| vix_level_class | PRE | low < 12.57 (p25), high > 18.24 (p75), else normal; percentiles of daily VIX closes 2021-10-20 to 2024-09-30 |
| vix_dir_class | PRE | rising >= +5 % over 5 sessions, falling <= -5 %, else flat |
| vix_chg1_sign | PRE | up if the one-day VIX change > 0 |
| gap_class | PRE | gap_down <= -0.3 %, gap_up >= +0.3 %, else flat |
| dte_class | PRE | sessions to expiry: 1, 2, 3, 4+ |
| breakout_time_class | PRE | before 10:00 (minutes after 09:30 < 30), 10:00-10:59, 11:00 or later |
| win | OUT | 1 if net_pct > 0 |

Notes
- Class boundaries come from NIFTY and VIX history 2021-10-20 to 2024-09-30 (727 sessions). The pre-registration says 2018 to 2024-09-30; the local store starts on 2021-10-20, so this is a stated deviation. Boundaries never use strategy returns.
- All cut definitions above were fixed before any outcome was tabulated.
- Missing values (not filled): pcr_oi 3, gift_basis 2, us_prev_ret 3, fut_oi_chg 1, fut_px_chg 1, fii_fut_longshare 1 (G1-F); stop_* fields only exist for stops.
