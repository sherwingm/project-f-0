# News and scheduled events

Index context research, 16 Nov 2026. Plan: `PREREG_CONTEXT.md`. Research only; nothing existing was changed; nothing committed. Net % = net per trade after costs (live-rule replays, 1 lot). Max up first.

Only scheduled events are available as timestamps (RBI / Budget / FOMC dates from Oct 2024, `scanner/s3_buy4`). No news archive with publication times exists in the repo; the GDELT tone series tested earlier (E-20261108-04) is a global daily number and is not used here. Categories such as inflation, GDP, geopolitics, reaction after 5 / 15 / 30 / 60 minutes and unexpected news were NOT tested: no timestamped source. `event_window` = the entry day or the next session is such a date (about 10-15 trades per set).

Discovery half only (entries to 2025-09-30); split at the discovery median. Verdict per factor is in `INDIVIDUAL_FACTOR_RESULTS.md`.

- G1-F (154) | event_window: high side -4.5 % (n 10, share reaching +100 % 30 %) vs low side +29.8 % (n 65, 49 %); difference -34.3 points, t -1.43, p 0.151, 95 % interval -78 to +11; multiple-testing pass: no
- G1 puts (259) | event_window: high side -10.9 % (n 15, share reaching +100 % 20 %) vs low side +10.9 % (n 113, 38 %); difference -21.8 points, t -1.24, p 0.215, 95 % interval -54 to +14; multiple-testing pass: no
- G1-C calls (235) | event_window: high side +13.6 % (n 16, share reaching +100 % 19 %) vs low side -7.4 % (n 96, 22 %); difference +21.0 points, t +1.01, p 0.314, 95 % interval -17 to +62; multiple-testing pass: no
- XP expiry-day straddle (107) | event_window: high side +4.0 % (n 7, share reaching +100 % 29 %) vs low side +0.1 % (n 45, 24 %); difference +3.9 points, t +0.15, p 0.884, 95 % interval -48 to +55; multiple-testing pass: no
