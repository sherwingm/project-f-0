# Index futures price and open interest

Index context research, 16 Nov 2026. Plan: `PREREG_CONTEXT.md`. Research only; nothing existing was changed; nothing committed. Net % = net per trade after costs (live-rule replays, 1 lot). Max up first.

Data: NIFTY near-month future from the daily bhavcopy (previous session vs the one before, same expiry). Quadrants (price up / OI up etc.) were not built separately; price and OI changes are tested as two numeric features. Futures minutes are not in the store.

Discovery half only (entries to 2025-09-30); split at the discovery median. Verdict per factor is in `INDIVIDUAL_FACTOR_RESULTS.md`.

- XP expiry-day straddle (107) | fut_px_chg: high side +23.7 % (n 26, share reaching +100 % 46 %) vs low side -22.4 % (n 26, 4 %); difference +46.1 points, t +2.05, p 0.040, 95 % interval +6 to +91; multiple-testing pass: no
- G1-C calls (235) | fut_oi_chg: high side -13.7 % (n 55, share reaching +100 % 18 %) vs low side +4.8 % (n 56, 25 %); difference -18.5 points, t -1.19, p 0.236, 95 % interval -50 to +12; multiple-testing pass: no
- XP expiry-day straddle (107) | fut_oi_chg: high side -12.4 % (n 26, share reaching +100 % 12 %) vs low side +13.6 % (n 26, 38 %); difference -25.9 points, t -1.12, p 0.262, 95 % interval -72 to +17; multiple-testing pass: no
- G1-F (154) | fut_px_chg: high side +15.2 % (n 37, share reaching +100 % 35 %) vs low side +37.4 % (n 37, 59 %); difference -22.2 points, t -0.92, p 0.358, 95 % interval -70 to +24; multiple-testing pass: no
- G1-F (154) | fut_oi_chg: high side +16.5 % (n 37, share reaching +100 % 46 %) vs low side +36.1 % (n 37, 49 %); difference -19.6 points, t -0.81, p 0.418, 95 % interval -66 to +28; multiple-testing pass: no
- G1-C calls (235) | fut_px_chg: high side +1.2 % (n 55, share reaching +100 % 18 %) vs low side -9.9 % (n 56, 25 %); difference +11.1 points, t +0.71, p 0.477, 95 % interval -20 to +43; multiple-testing pass: no
- G1 puts (259) | fut_oi_chg: high side +4.2 % (n 63, share reaching +100 % 37 %) vs low side +13.4 % (n 64, 36 %); difference -9.2 points, t -0.53, p 0.594, 95 % interval -43 to +25; multiple-testing pass: no
- G1 puts (259) | fut_px_chg: high side +4.9 % (n 63, share reaching +100 % 32 %) vs low side +12.7 % (n 64, 41 %); difference -7.8 points, t -0.45, p 0.652, 95 % interval -41 to +27; multiple-testing pass: no
