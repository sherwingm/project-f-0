# FII positioning (index futures)

Index context research, 16 Nov 2026. Plan: `PREREG_CONTEXT.md`. Research only; nothing existing was changed; nothing committed. Net % = net per trade after costs (live-rule replays, 1 lot). Max up first.

Data: NSE participant open-interest files (previous session). FII / DII cash buy-sell flows are not available historically; DII is not tested separately. This repeats E-20261108-05 / E-20261109-01 (no candidate) on the trade sets.

Discovery half only (entries to 2025-09-30); split at the discovery median. Verdict per factor is in `INDIVIDUAL_FACTOR_RESULTS.md`.

- XP expiry-day straddle (107) | fii_fut_longshare: high side +15.5 % (n 26, share reaching +100 % 27 %) vs low side -14.3 % (n 26, 23 %); difference +29.7 points, t +1.29, p 0.197, 95 % interval -12 to +77; multiple-testing pass: no
- G1-C calls (235) | fii_fut_chg: high side +3.7 % (n 55, share reaching +100 % 24 %) vs low side -12.3 % (n 56, 20 %); difference +16.0 points, t +1.02, p 0.308, 95 % interval -14 to +46; multiple-testing pass: no
- G1 puts (259) | fii_fut_longshare: high side +16.1 % (n 63, share reaching +100 % 38 %) vs low side +1.6 % (n 64, 34 %); difference +14.5 points, t +0.84, p 0.403, 95 % interval -20 to +49; multiple-testing pass: no
- G1-F (154) | fii_fut_longshare: high side +34.7 % (n 37, share reaching +100 % 51 %) vs low side +17.9 % (n 37, 43 %); difference +16.8 points, t +0.69, p 0.489, 95 % interval -30 to +65; multiple-testing pass: no
- XP expiry-day straddle (107) | fii_fut_chg: high side -6.2 % (n 26, share reaching +100 % 31 %) vs low side +7.4 % (n 26, 19 %); difference -13.6 points, t -0.58, p 0.560, 95 % interval -61 to +29; multiple-testing pass: no
- G1-C calls (235) | fii_fut_longshare: high side -8.5 % (n 55, share reaching +100 % 22 %) vs low side -0.3 % (n 56, 21 %); difference -8.2 points, t -0.52, p 0.603, 95 % interval -40 to +23; multiple-testing pass: no
- G1 puts (259) | fii_fut_chg: high side +10.4 % (n 63, share reaching +100 % 32 %) vs low side +7.3 % (n 64, 41 %); difference +3.1 points, t +0.18, p 0.858, 95 % interval -30 to +38; multiple-testing pass: no
- G1-F (154) | fii_fut_chg: high side +24.3 % (n 37, share reaching +100 % 43 %) vs low side +28.3 % (n 37, 51 %); difference -4.0 points, t -0.16, p 0.869, 95 % interval -51 to +43; multiple-testing pass: no
