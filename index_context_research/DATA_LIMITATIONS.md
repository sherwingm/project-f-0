# Data limitations (index context research, 16 Nov 2026)

- **Trade records:** only NIFTY, only history replays (G1 259, G1-F 154, G1-C 235 priced of 240 signals, XP 107 expiry days), Oct 2024 to Oct 2026. No BANKNIFTY / SENSEX option-trade records for these rules; the live ledgers are on the VM (off limits). Near Tighty is the 1-3-session subset of G1, not a separate set.
- **Years:** the option minute data starts Oct 2024, so the yearly tables have 2024 (3 months), 2025 and 2026 (partial). 2021-2023 cannot be tested for these strategies.
- **Indices:** FINNIFTY, MIDCPNIFTY, BANKEX have only GIFT futures settlements (no spot, no option history here). Not tested.
- **GIFT Nifty:** daily settlement prices only (861 days from 10 Jul 2023); the 09:00 pre-open level, overnight path and intraday history do not exist in the data. `gift_basis` and `gift_ret_prev` are daily proxies and say nothing about the actual opening gap.
- **FII / DII:** participant open-interest positions only (previous session). Cash-market flows are not available historically; DII was not tested separately.
- **News:** no timestamped news archive. Only scheduled RBI / Budget / FOMC dates from Oct 2024; GDELT daily tone is a global machine score. News categories, 5-60 minute reactions and unexpected news were not tested.
- **Futures:** daily bhavcopy (price, OI) only; no futures minutes, no GIFT OI by participant. Price/OI quadrants were not built separately.
- **Options data:** last-trade prices and OI by the minute; no bid / ask, no real implied volatility (Black-Scholes IV from the last price, noisy on thin strikes). The replay engine's slippage is flat (0.5 % / 1 %).
- **Breadth:** today's F&O list applied to the past (survivorship bias); NIFTY 50 constituents at the time, heavyweight contribution and sector participation were not built.
- **US overnight:** S&P 500 daily closes cached to 2026-09-25; later trades have a missing value (never zero).
- **Sample size and looks:** 107-259 trades per set, 67 cells tested here, and about 420+ earlier looks at the same NIFTY option data; a pass could only be a lead.
- **Process notes:** the first analysis run skipped XP through a rule that was not in the plan (n < 60); corrected before validation was opened. Nothing was committed, per the mission; `experiments.csv` was not appended (existing file), so the registry row is in `HYPOTHESIS_REGISTRY.md` / `EXPERIMENT_MANIFEST.json` instead.
