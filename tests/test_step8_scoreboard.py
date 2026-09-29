"""Step 8: honest scoreboard. Build data (index closes, daily volume ratios), the ledger's one-group stats,
and the page's scoring rules, run in node straight from the template."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from scanner.binomial import binomial_line, hits_needed
from scanner.equity import equity_metrics_one, index_closes
from server.paper import trade_stats

ROOT = Path(__file__).resolve().parent.parent


def test_hits_needed_matches_the_published_table():
    assert [hits_needed(n) for n in (50, 100, 200, 400)] == [31, 59, 112, 217]
    assert "31/50, 59/100, 112/200, 217/400" in binomial_line(30, 50)
    assert binomial_line(31, 50).endswith("clears it") and binomial_line(30, 50).endswith("does not clear it")


def test_equity_rows_carry_daily_volume_ratios_aligned_with_the_chart():
    dates = pd.bdate_range("2026-07-01", periods=60)
    vol = [1000.0] * 59 + [3000.0]
    df = pd.DataFrame({"Open": 1, "High": 1, "Low": 1, "Close": range(100, 160), "Volume": vol}, index=dates)
    m = equity_metrics_one("ABC", df)
    assert len(m["chart_volume_ratios"]) == len(m["chart_dates"]) == 30
    assert m["chart_volume_ratios"][-1] == 3.0 == m["volume_ratio"] and m["chart_volume_ratios"][0] == 1.0


def test_index_closes_reads_eod2_index_file_up_to_the_scan_date(tmp_path):
    days = pd.bdate_range("2026-07-01", periods=45)
    pd.DataFrame({"Date": days.strftime("%Y-%m-%d"), "Open": 1, "High": 1, "Low": 1, "Close": range(20000, 20045),
                  "Volume": 1, "P/E": 20, "Series": None}).to_csv(tmp_path / "nifty 50.csv", index=False)
    out = index_closes(tmp_path, as_of=days[40])
    assert out["name"] == "NIFTY 50" and len(out["closes"]) == 30
    assert out["dates"][-1] == days[40].strftime("%Y-%m-%d") and out["closes"][-1] == 20040
    assert index_closes(tmp_path, as_of=days[40], name="no such index") is None      # falls back to none


def test_trade_stats_are_one_group():
    t = lambda net, ret: {"net_pnl": net, "return_pct": ret, "charges_total": 50}
    s = trade_stats([t(100, 5), t(-50, -2.5), t(900, 300), t(-40, -100)])
    assert set(s) == {"all"}                                         # DECISIONS.md: no buckets
    assert s["all"]["trades"] == 4 and s["all"]["wins"] == 2 and s["all"]["total_net_pnl"] == 910
    assert s["all"]["win_rate"] == 50.0 and s["all"]["hits_needed"] == hits_needed(4)
    assert s["all"]["total_charges"] == 200


# ---------------------------------------------------------------- the page's scoring rules, in node
NODE = shutil.which("node")
SCORING = re.search(r'<script id="scoring">(.*?)</script>', (ROOT / "templates" / "index.html").read_text(encoding="utf-8"), re.S).group(1)

JS_TESTS = r"""
const out = {};
out.needed = [50, 100, 200, 400].map(Scoring.needed);
out.refLine = Scoring.refLine();
const dates = ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-07", "2026-09-08", "2026-09-09"];
const cal = Scoring.calendar([dates]);
out.between = [cal.between("2026-09-01", "2026-09-04"), cal.between("2026-09-01", "2026-09-10")];
const index = { dates, closes: [1000, 1002, 1005, 1010, 1010, 1010, 1010] };
out.adjusted = Scoring.adjusted(dates, [100, 101, 102, 103, 103, 103, 103], index, "2026-09-01", 3);   // +3% - 1%
out.raw = Scoring.adjusted(dates, [100, 101, 102, 103, 103, 103, 103], null, "2026-09-01", 3);
const items = [
  { symbol: "A", as_of: "2026-09-01", dir: "bullish", move: 2.0 },    // hit
  { symbol: "A", as_of: "2026-09-03", dir: "bullish", move: 5.0 },    // within 3 sessions of the first: duplicate
  { symbol: "A", as_of: "2026-09-04", dir: "bearish", move: 1.5 },    // 3 sessions later: scored, miss
  { symbol: "B", as_of: "2026-09-01", dir: "bearish", move: -0.4 },   // inside the threshold: not scored
  { symbol: "C", as_of: "2026-09-01", dir: "neutral", move: 3.0 },    // no direction: not scored
  { symbol: "D", as_of: "2026-09-02", dir: "bearish", move: null },   // waiting for data
  { symbol: "E", as_of: "2026-09-02", dir: "bearish", move: -1.2 },   // hit
];
const s = Scoring.score(items, cal, 1.0);
out.score = { n: s.n, hits: s.hits, dup: s.dup, small: s.small, nodir: s.nodir, pending: s.pending, needed: s.needed, clears: s.clears,
              statuses: s.rows.map(r => r.symbol + "@" + r.as_of.slice(8) + ":" + r.status) };
const stocks = [];
for (let k = 0; k < 12; k++) stocks.push({ symbol: "S" + String(k).padStart(2, "0"), chart_dates: dates,
  chart_closes: [100, 100, 100, 100 + k, 100 + k, 100 + k, 100 + k], chart_volume_ratios: dates.map(() => k) });
const base = Scoring.baseline(stocks, cal, index, 3);
out.baselineFirstDay = base.filter(b => b.as_of === "2026-09-01").map(b => b.symbol);
const bs = Scoring.score(base, cal, 1.0);
out.baseline = { n: bs.n, hits: bs.hits, dup: bs.dup };
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_page_scoring_rules_in_node(tmp_path):
    f = tmp_path / "t.js"
    f.write_text(SCORING + "\n" + JS_TESTS, encoding="utf-8")
    out = json.loads(subprocess.run([NODE, str(f)], capture_output=True, text=True, check=True).stdout)
    assert out["needed"] == [31, 59, 112, 217]
    assert out["refLine"].endswith("31/50, 59/100, 112/200, 217/400")
    assert out["between"] == [3, 7]                          # known sessions, then weekdays past the calendar
    assert out["adjusted"] == 2.0 and out["raw"] == 3.0       # (103/100 - 1) - (1010/1000 - 1), and unadjusted
    sc = out["score"]
    assert (sc["n"], sc["hits"], sc["dup"], sc["small"], sc["nodir"], sc["pending"]) == (3, 2, 1, 1, 1, 1)
    assert sc["needed"] == 3 and sc["clears"] is False
    assert "A@03:dup" in sc["statuses"] and "A@04:miss" in sc["statuses"] and "E@02:hit" in sc["statuses"]
    # baseline: the ten highest volume ratios (S02..S11) on each day, all called bullish
    assert out["baselineFirstDay"] == [f"S{k:02d}" for k in range(11, 1, -1)]
    # day 1 and day 4 are scored (3 sessions apart); days 2-3 are duplicates. Day-1 moves: S02..S11 gain k% vs the
    # index's 1%: S02 is +1% adjusted (inside +-1%), S03..S11 are hits. Day-4 onwards the closes are flat: -0% vs
    # index 0% -> within the threshold. So 9 scored, 9 hits.
    assert out["baseline"]["n"] == 9 and out["baseline"]["hits"] == 9
