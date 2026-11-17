# India VIX

Index context research, 16 Nov 2026. Plan: `PREREG_CONTEXT.md`. Research only; nothing existing was changed; nothing committed. Net % = net per trade after costs (live-rule replays, 1 lot). Max up first.

Data: VIX 1-minute and daily (store). Repeats parts of the stress audit regimes and the G1 searches; included for the unified table.

Discovery half only (entries to 2025-09-30); split at the discovery median. Verdict per factor is in `INDIVIDUAL_FACTOR_RESULTS.md`.

- XP expiry-day straddle (107) | vix_chg5: high side -38.0 % (n 26, share reaching +100 % 8 %) vs low side +39.2 % (n 26, 42 %); difference -77.2 points, t -3.73, p 0.000, 95 % interval -121 to -38; multiple-testing pass: YES
- G1-C calls (235) | vix_chg5: high side -19.0 % (n 56, share reaching +100 % 18 %) vs low side +10.3 % (n 56, 25 %); difference -29.4 points, t -1.92, p 0.055, 95 % interval -59 to -0; multiple-testing pass: no
- G1 puts (259) | vix_pct1y: high side -8.0 % (n 63, share reaching +100 % 27 %) vs low side +24.2 % (n 65, 45 %); difference -32.1 points, t -1.90, p 0.057, 95 % interval -63 to +0; multiple-testing pass: no
- G1 puts (259) | vix_chg5: high side -7.4 % (n 64, share reaching +100 % 33 %) vs low side +24.1 % (n 64, 39 %); difference -31.6 points, t -1.86, p 0.063, 95 % interval -65 to +2; multiple-testing pass: no
- G1 puts (259) | vix_signal: high side -5.0 % (n 64, share reaching +100 % 27 %) vs low side +21.7 % (n 64, 45 %); difference -26.7 points, t -1.56, p 0.118, 95 % interval -59 to +7; multiple-testing pass: no
- G1-C calls (235) | vix_pct1y: high side -11.7 % (n 56, share reaching +100 % 20 %) vs low side +3.0 % (n 56, 23 %); difference -14.7 points, t -0.95, p 0.344, 95 % interval -46 to +15; multiple-testing pass: no
- G1-C calls (235) | vix_signal: high side -10.8 % (n 56, share reaching +100 % 20 %) vs low side +2.1 % (n 56, 23 %); difference -12.9 points, t -0.83, p 0.405, 95 % interval -44 to +17; multiple-testing pass: no
- XP expiry-day straddle (107) | vix_pct1y: high side -6.3 % (n 26, share reaching +100 % 19 %) vs low side +7.6 % (n 26, 31 %); difference -13.9 points, t -0.60, p 0.552, 95 % interval -55 to +32; multiple-testing pass: no
- XP expiry-day straddle (107) | vix_signal: high side -3.1 % (n 26, share reaching +100 % 19 %) vs low side +4.4 % (n 26, 31 %); difference -7.5 points, t -0.32, p 0.749, 95 % interval -50 to +40; multiple-testing pass: no
- G1-F (154) | vix_pct1y: high side +28.2 % (n 37, share reaching +100 % 49 %) vs low side +22.3 % (n 38, 45 %); difference +5.9 points, t +0.24, p 0.807, 95 % interval -38 to +52; multiple-testing pass: no
- G1-F (154) | vix_signal: high side +28.1 % (n 37, share reaching +100 % 49 %) vs low side +22.5 % (n 38, 45 %); difference +5.6 points, t +0.23, p 0.816, 95 % interval -41 to +50; multiple-testing pass: no
- G1-F (154) | vix_chg5: high side +22.8 % (n 37, share reaching +100 % 51 %) vs low side +27.7 % (n 38, 42 %); difference -4.9 points, t -0.20, p 0.838, 95 % interval -53 to +38; multiple-testing pass: no
