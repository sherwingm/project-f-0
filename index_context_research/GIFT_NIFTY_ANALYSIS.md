# GIFT Nifty (basis and overnight move)

Index context research, 16 Nov 2026. Plan: `PREREG_CONTEXT.md`. Research only; nothing existing was changed; nothing committed. Net % = net per trade after costs (live-rule replays, 1 lot). Max up first.

Data: NSE IX daily settlement prices (fetched 16 Nov, 861 days from 10 Jul 2023). **Daily settlements, not the pre-open level**: `gift_basis` = previous settlement vs NIFTY previous close; `gift_ret_prev` = previous session's settlement change. Neither is the 09:00 gap, so the question 'does GIFT predict the opening' is NOT answered here. `gift_basis_dev` (basis minus its 20-day mean) was planned but not built.

Discovery half only (entries to 2025-09-30); split at the discovery median. Verdict per factor is in `INDIVIDUAL_FACTOR_RESULTS.md`.

- XP expiry-day straddle (107) | gift_ret_prev: high side +24.0 % (n 25, share reaching +100 % 52 %) vs low side -24.6 % (n 26, 0 %); difference +48.6 points, t +2.11, p 0.035, 95 % interval +5 to +96; multiple-testing pass: no
- G1-F (154) | gift_ret_prev: high side +11.6 % (n 36, share reaching +100 % 39 %) vs low side +36.8 % (n 37, 54 %); difference -25.2 points, t -1.05, p 0.295, 95 % interval -72 to +18; multiple-testing pass: no
- G1-C calls (235) | gift_ret_prev: high side +2.9 % (n 55, share reaching +100 % 20 %) vs low side -11.8 % (n 55, 24 %); difference +14.7 points, t +0.93, p 0.352, 95 % interval -16 to +45; multiple-testing pass: no
- XP expiry-day straddle (107) | gift_basis: high side -7.8 % (n 25, share reaching +100 % 28 %) vs low side +5.9 % (n 26, 23 %); difference -13.7 points, t -0.58, p 0.560, 95 % interval -62 to +29; multiple-testing pass: no
- G1 puts (259) | gift_ret_prev: high side +3.3 % (n 63, share reaching +100 % 29 %) vs low side +11.9 % (n 63, 43 %); difference -8.6 points, t -0.50, p 0.618, 95 % interval -44 to +26; multiple-testing pass: no
- G1 puts (259) | gift_basis: high side +4.8 % (n 63, share reaching +100 % 29 %) vs low side +10.4 % (n 63, 43 %); difference -5.6 points, t -0.32, p 0.745, 95 % interval -40 to +29; multiple-testing pass: no
- G1-C calls (235) | gift_basis: high side -6.4 % (n 55, share reaching +100 % 22 %) vs low side -2.5 % (n 55, 22 %); difference -3.9 points, t -0.25, p 0.806, 95 % interval -35 to +25; multiple-testing pass: no
- G1-F (154) | gift_basis: high side +23.2 % (n 36, share reaching +100 % 39 %) vs low side +25.5 % (n 37, 54 %); difference -2.3 points, t -0.09, p 0.926, 95 % interval -49 to +47; multiple-testing pass: no
