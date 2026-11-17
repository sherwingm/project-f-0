# Index breadth proxy

Index context research, 16 Nov 2026. Plan: `PREREG_CONTEXT.md`. Research only; nothing existing was changed; nothing committed. Net % = net per trade after costs (live-rule replays, 1 lot). Max up first.

**Survivorship-biased proxy**: share of TODAY's F&O list that closed up on the previous session (`data/eod2`), not NIFTY 50 constituents at the time. Heavyweight contribution and sector participation were not built. Do not trust beyond a lead.

Discovery half only (entries to 2025-09-30); split at the discovery median. Verdict per factor is in `INDIVIDUAL_FACTOR_RESULTS.md`.

- G1 puts (259) | breadth_prev: high side -7.0 % (n 64, share reaching +100 % 25 %) vs low side +23.7 % (n 64, 47 %); difference -30.7 points, t -1.81, p 0.071, 95 % interval -65 to +2; multiple-testing pass: no
- G1-C calls (235) | breadth_prev: high side +8.9 % (n 56, share reaching +100 % 23 %) vs low side -17.6 % (n 56, 20 %); difference +26.5 points, t +1.73, p 0.084, 95 % interval -3 to +56; multiple-testing pass: no
- XP expiry-day straddle (107) | breadth_prev: high side +19.8 % (n 26, share reaching +100 % 38 %) vs low side -18.6 % (n 26, 12 %); difference +38.5 points, t +1.69, p 0.091, 95 % interval -3 to +86; multiple-testing pass: no
- G1-F (154) | breadth_prev: high side +36.7 % (n 36, share reaching +100 % 42 %) vs low side +14.6 % (n 39, 51 %); difference +22.1 points, t +0.92, p 0.360, 95 % interval -25 to +70; multiple-testing pass: no
