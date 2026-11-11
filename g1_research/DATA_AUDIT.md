# Audit of the 1-minute data behind the G1 / G1-F history (2026-11-11, the user: "recheck the 1min data, is everything present or any mistake")
Script: scripts/audit_1min_data.py (+ the checks below, run inline). Outputs: results/data_audit_*.csv. Read-only; nothing changed. Window 2021-10-20 to 2026-10-28; G1 days are 2024-10 on.

## NIFTY spot 1-minute (1,240 sessions, 465,844 bars)
- 1,238 sessions complete (375-376 bars). Two partial sessions, both in Nov 2021, before any G1 day: 4 Nov 2021 (43 bars) and 10 Nov 2021 (18 minutes missing). Total missing minutes in complete sessions: 3.
- 0 duplicate timestamps, 0 bars with high / low inconsistent with open / close, 0 zero or empty prices. Biggest 1-minute move 0.87 % (7 Apr 2025). No 2026 weekday without data except holidays.
- Weekend sessions present: 20 Jan 2024, 1 Feb 2025, 1 Feb 2026 (special / Budget sessions, real). The two evening Muhurat sessions (24 Oct 2022, 1 Nov 2024) are in the daily file but not in the minute file: they were never traded.
- Against the independent daily file (to 2025-09-30): minute-derived close differs by 0.04 % median (the official close is an average of the last half hour, so small gaps are normal). Two days differ by more than 0.5 % (19 Apr 2022, 4 Jun 2024); on 4 Jun 2024 the minute close (21,884.5) is the widely reported close, so the daily file looks off there, not the minute file.
- **Found, and explained: since 3 Aug 2026 the index is flat from 15:15 to 15:28 every session** (61 sessions; the bars show one repeated value, then the last bar jumps to the closing value). The LIVE 1-second recorder shows the same on 6 Nov (24,938.9 for all 14 minutes, then 25,030.35 at 15:29): NSE's index feed itself is frozen in that window, so it is the feed, not a gap or an error in our files. G1 is not affected: signals are before 13:00 (0 % flat bars before any of the 259 signals) and exits use option prices, which keep trading.

## India VIX 1-minute (1,241 days)
- Values 9.08 to 33.85, no zero / empty. Two partial days (the same two in Nov 2021). 48 one-minute jumps above 5 % (max 16 %), all around opens and event days. The last minute vs the daily close: median 0.37 % (24 of 1,229 days above 2 %); VIX is only used as a level at the signal, with the 17 threshold.

## Option minutes on the 259 G1 days (the traded ATM put)
- Option file present on 259 of 259 days; the entry-minute bar present on 259 of 259; from entry to 15:29 a median of 354 bars and never a gap above 1 minute.
- 0 high / low inconsistencies, 0 zero or negative prices, 0 duplicate timestamps, 0 one-minute jumps above 50 %.
- Sources: 256 days Upstox, 2 Kotak, 1 both (merged as `index_data.merge_sources` does: Kotak if it has any row for the contract, else Upstox; zero-volume Upstox rows dropped).
- "Below intrinsic" check (put priced under K minus spot): 374 bars on 16 days. Cause: options price off the FORWARD, not spot; implied forward minus spot (K + call - put - spot) has median +21 points (MAD 14-18) over the trades, so a put can sit 20-30 points under K minus spot. Larger ones: 29 May 2026 15:10-15:25 (put 100+ points under, the spot dipped to 23,517 while the options imply about 23,700: one day, spot glitch or a brief index print, no G1 decision used spot then) and exit-day closes affected by the frozen spot above (e.g. 3 Aug 2026). No option price itself looked wrong.

## What it does NOT cover
No second vendor for option prices (the check is internal consistency: gaps, ranges, parity), no bid / ask in the history (trade prices only, see the replay caveat), and the 1-second recorder only exists from 2 Nov 2026.

## Verdict
The 1-minute history behind G1 / G1-F is complete and internally consistent for every G1 day. The two real findings (partial days in 2021, and the frozen index 15:15-15:28 since Aug 2026) do not touch any G1 trade, signal or exit. No result needs re-running.
