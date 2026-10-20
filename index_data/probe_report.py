"""Rewrite the "Expired-token retention" table of INDEX_DATA_REPORT.md from data/index/probe_expired.json.

    python -m index_data.probe_report

The table keeps its header and its first row (the pre-expiry baseline from DATA_ACCESS_AUDIT); every probe result in
probe_expired.json becomes one row after it, oldest first. Run by .github/workflows/kotak-probes.yml after each probe.
"""
from __future__ import annotations

from .common import ROOT, SMALL, read_json

REPORT = ROOT / "INDEX_DATA_REPORT.md"
SECTION = "## Expired-token retention"


def row(i: int, h: dict) -> str:
    c = {x["check"]: x for x in h.get("checks", [])}
    rows = lambda k: (str(c[k]["rows"]) if not c[k].get("error") else f"error: {c[k]['error'][:60]}") if k in c else "—"  # noqa: E731
    listed = c.get("still in the scrip master", {}).get("result")
    listed = "yes" if listed is True else "no" if listed is False else str(listed)
    return (f"| probe {i} | {h.get('label') or h.get('run_on')} (run {h.get('run_on')}) | {rows('1min before expiry')} | "
            f"{rows('1min expiry day')} | {rows('5min')} | {rows('daily')} | {listed} | "
            f"{rows('control: NIFTY 50 spot 1min expiry day')} | {h.get('verdict')} |")


def render(text: str, hist: list[dict]) -> str:
    lines = text.split("\n")
    s = lines.index(SECTION)
    t = next(i for i in range(s, len(lines)) if lines[i].startswith("| Probe"))
    end = t
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    keep = lines[t:t + 3]                                  # header, separator, the pre-expiry baseline row
    return "\n".join(lines[:t] + keep + [row(i + 1, h) for i, h in enumerate(hist)] + lines[end:])


def main() -> None:
    hist = read_json(SMALL / "probe_expired.json", []) or []
    REPORT.write_text(render(REPORT.read_text(encoding="utf-8"), hist), encoding="utf-8")
    print(f"{len(hist)} probe rows written")


if __name__ == "__main__":
    main()
