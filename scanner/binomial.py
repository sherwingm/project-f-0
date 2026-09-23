"""How many hits out of N it takes to beat a coin flip (one-sided, about 95%): N/2 + 1.645 * sqrt(N) / 2,
rounded up. 31/50, 59/100, 112/200, 217/400. Shared by the page's scoreboard (same formula in JS), the
paper ledger's trade stats and the cheap-option backtest."""
from __future__ import annotations

import math

REFERENCE_NS = (50, 100, 200, 400)


def hits_needed(n: int) -> int | None:
    return math.ceil(n / 2 + 1.645 * math.sqrt(n) / 2) if n > 0 else None


def reference_line() -> str:
    return "hits needed to beat a coin at this N: " + ", ".join(f"{hits_needed(n)}/{n}" for n in REFERENCE_NS)


def binomial_line(hits: int, n: int) -> str:
    """One line: the reference table plus whether `hits` of `n` clears the bar for this N."""
    if n <= 0:
        return reference_line() + "; nothing scored yet"
    need = hits_needed(n)
    verdict = "clears it" if hits >= need else "does not clear it"
    return f"{reference_line()}; here {hits}/{n}, needs {need}: {verdict}"
