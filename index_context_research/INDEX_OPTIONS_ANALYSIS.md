# Index options at the entry minute (IV, put-call OI, skew)

Index context research, 16 Nov 2026. Plan: `PREREG_CONTEXT.md`. Research only; nothing existing was changed; nothing committed. Net % = net per trade after costs (live-rule replays, 1 lot). Max up first.

Data: NIFTY option 1-minute prices and OI at the entry minute; IV by Black-Scholes (r 6.5 %, no dividends) from the last traded price, so thin-trading strikes add noise. Bid-ask spreads are not in the history. Ablation between IV, OI and skew was not run (see COMBINATION_ANALYSIS.md).

Discovery half only (entries to 2025-09-30); split at the discovery median. Verdict per factor is in `INDIVIDUAL_FACTOR_RESULTS.md`.

- G1-C calls (235) | pcr_oi: high side +15.9 % (n 56, share reaching +100 % 21 %) vs low side -24.6 % (n 56, 21 %); difference +40.5 points, t +2.69, p 0.007, 95 % interval +11 to +70; multiple-testing pass: no
- G1 puts (259) | atm_iv: high side -12.8 % (n 64, share reaching +100 % 30 %) vs low side +29.5 % (n 64, 42 %); difference -42.3 points, t -2.52, p 0.012, 95 % interval -76 to -9; multiple-testing pass: no
- G1-C calls (235) | atm_iv: high side +11.5 % (n 56, share reaching +100 % 27 %) vs low side -20.2 % (n 56, 16 %); difference +31.7 points, t +2.07, p 0.038, 95 % interval +2 to +62; multiple-testing pass: no
- G1-F (154) | iv_skew: high side +42.3 % (n 37, share reaching +100 % 57 %) vs low side +8.6 % (n 38, 37 %); difference +33.7 points, t +1.41, p 0.158, 95 % interval -10 to +79; multiple-testing pass: no
- XP expiry-day straddle (107) | iv_skew: high side -12.9 % (n 26, share reaching +100 % 27 %) vs low side +14.1 % (n 26, 23 %); difference -27.0 points, t -1.17, p 0.243, 95 % interval -73 to +15; multiple-testing pass: no
- G1 puts (259) | iv_skew: high side +16.9 % (n 64, share reaching +100 % 42 %) vs low side -0.2 % (n 64, 30 %); difference +17.2 points, t +1.00, p 0.317, 95 % interval -15 to +50; multiple-testing pass: no
- G1-F (154) | pcr_oi: high side +33.0 % (n 37, share reaching +100 % 46 %) vs low side +17.7 % (n 38, 47 %); difference +15.3 points, t +0.64, p 0.523, 95 % interval -30 to +61; multiple-testing pass: no
- XP expiry-day straddle (107) | atm_iv: high side -6.6 % (n 26, share reaching +100 % 27 %) vs low side +7.8 % (n 26, 23 %); difference -14.4 points, t -0.62, p 0.538, 95 % interval -60 to +29; multiple-testing pass: no
- XP expiry-day straddle (107) | pcr_oi: high side +7.3 % (n 26, share reaching +100 % 31 %) vs low side -6.0 % (n 26, 19 %); difference +13.3 points, t +0.57, p 0.568, 95 % interval -30 to +59; multiple-testing pass: no
- G1-F (154) | atm_iv: high side +19.8 % (n 37, share reaching +100 % 46 %) vs low side +30.6 % (n 38, 47 %); difference -10.8 points, t -0.45, p 0.654, 95 % interval -59 to +34; multiple-testing pass: no
- G1-C calls (235) | iv_skew: high side -7.0 % (n 56, share reaching +100 % 20 %) vs low side -1.7 % (n 56, 23 %); difference -5.2 points, t -0.33, p 0.738, 95 % interval -36 to +26; multiple-testing pass: no
- G1 puts (259) | pcr_oi: high side +5.7 % (n 64, share reaching +100 % 36 %) vs low side +11.0 % (n 64, 36 %); difference -5.3 points, t -0.31, p 0.759, 95 % interval -38 to +27; multiple-testing pass: no
