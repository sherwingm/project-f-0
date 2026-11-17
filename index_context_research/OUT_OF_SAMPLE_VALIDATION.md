# Out-of-sample validation

Index context research, 16 Nov 2026. Plan: `PREREG_CONTEXT.md`. Research only; nothing existing was changed; nothing committed. Net % = net per trade after costs (live-rule replays, 1 lot). Max up first.

Validation (entries from 2025-10-01 to 2026-10-28) was opened once, for the frozen survivors only. Pass rule: the same side is better, |t| >= 1.5 in the same direction, the better side's mean is > 0, n >= 20.

- XP expiry-day straddle (107) | vix_chg5: discovery difference -77.2; validation high n 29 / low n 26, difference +22.8 points (t +1.23); better side's mean -23.0 % -> FAILED (sign reversed)

No walk-forward beyond this one chronological split was run (sample too small). Costs and slippage are those of the replay engine (0.5 % / 1 %, dated charges).
