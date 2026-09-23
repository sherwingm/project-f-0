"""Build the scan: one command produces data/scan.json and a self-contained docs/index.html.

    python -m scanner.build                # live: NSE universe + eod2 prices + NSE F&O bhavcopy
    python -m scanner.build --skip-fo      # offline/blocked: prices & volume only, labels Unclassified

The HTML is a single file with the JSON embedded, so it can be hosted anywhere static
(GitHub Pages, Render static site, Netlify) or opened straight from a phone's file manager.
"""
from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

from .classify import BULLISH, BEARISH, NEUTRAL, UNCLASSIFIED, classify
from .equity import equity_metrics, index_closes
from .nse_fo import BhavcopyUnavailable, download_fo_bhavcopy, fo_metrics
from .commentary import generate_commentary
from .strikes import option_chains
from .universe import fetch_fo_lots

ROOT = Path(__file__).resolve().parent.parent
IST = timezone(timedelta(hours=5, minutes=30))
log = logging.getLogger("scanner")

DISCLAIMER = ("This is a data scan based on previous session's closing data. Labels describe common "
              "interpretations of OI/volume/PCR patterns — they are not trade recommendations, entry/exit "
              "signals, or predictions. F&O trading carries high risk including potential loss beyond "
              "capital invested.")


def build(eod2_dir: Path, cache_dir: Path, skip_fo: bool = False, commentary: bool = False) -> dict:
    lots = fetch_fo_lots(cache_path=cache_dir / "fo_universe.txt")
    universe = sorted(lots)

    as_of, rows = equity_metrics(universe, local_dir=eod2_dir)
    log.info("equity metrics for %d/%d stocks as of %s", len(rows), len(universe), as_of.date())
    index = index_closes(eod2_dir, as_of)
    if index and index["dates"][-1] != as_of.strftime("%Y-%m-%d"):
        log.warning("index %s ends %s, before the scan date %s", index["name"], index["dates"][-1], as_of.date())

    fo_status = "ok"
    chain_status = "ok"
    fo = pd.DataFrame(columns=["symbol"])
    chains: dict[str, dict] = {}
    chain_problems: dict[str, str] = {}
    if skip_fo:
        fo_status = chain_status = "skipped (--skip-fo)"
    else:
        try:
            bhav = download_fo_bhavcopy(as_of.date(), cache_dir=cache_dir)
        except BhavcopyUnavailable as exc:
            fo_status = chain_status = f"unavailable: {exc}"
            log.error("F&O bhavcopy: %s", exc)
        except Exception as exc:  # noqa: BLE001 - network errors must not kill the equity build
            fo_status = chain_status = f"error: {exc}"
            log.error("F&O bhavcopy: %s", exc)
        else:
            # Step 1: futures OI, OI change, PCR. This is what the labels depend on.
            try:
                fo = fo_metrics(bhav)
                log.info("F&O metrics for %d stocks from bhavcopy %s", len(fo), as_of.date())
            except Exception as exc:  # noqa: BLE001
                fo_status = f"error: {exc}"
                log.error("F&O metrics: %s", exc)
            # Step 2: strike tables. Independent of step 1; a failure here never touches the labels.
            try:
                chains, chain_problems = option_chains(bhav, {r["symbol"]: r["close"] for r in rows})
                log.info("option chains for %d stocks (%d skipped)", len(chains), len(chain_problems))
            except Exception as exc:  # noqa: BLE001
                chain_status = f"error: {exc}"
                log.error("option chains: %s", exc)

    fo_by_symbol = {r["symbol"]: r for r in fo.to_dict("records")} if len(fo) else {}
    stocks = []
    for r in rows:
        f = fo_by_symbol.get(r["symbol"], {})
        r.update({
            "fut_oi": _int(f.get("fut_oi")),
            "fut_oi_prev": _int(f.get("fut_oi_prev")),
            "oi_change_pct": _round(f.get("oi_change_pct")),
            "call_oi": _int(f.get("call_oi")),
            "put_oi": _int(f.get("put_oi")),
            "pcr": _round(f.get("pcr")),
        })
        r.update(classify(r))
        r["lot_size"] = lots.get(r["symbol"]) or None
        r["chain"] = chains.get(r["symbol"])
        stocks.append(r)
    stocks.sort(key=lambda s: s["symbol"])

    counts = Counter(s["label"] for s in stocks)
    scan = {
        "meta": {
            "as_of": as_of.strftime("%Y-%m-%d"),
            "as_of_label": as_of.strftime("%a %d %b %Y"),
            "generated_at_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
            "universe_size": len(universe),
            "stocks_with_data": len(stocks),
            "missing_symbols": sorted(set(universe) - {s["symbol"] for s in stocks}),
            "fo_status": fo_status,
            "fo_available": fo_status == "ok",
            "chain_status": chain_status,
            "chain_available": chain_status == "ok",
            "fo_warnings": _fo_warnings(stocks, fo_status, chain_status, chain_problems),
            "chains_available": bool(chains),
            "sources": {
                "universe": "NSE fo_mktlots.csv (live)",
                "prices_volume": "NSE bhavcopy via BennyThadikaran/eod2_data (Quantis pipeline)",
                "oi_pcr": "NSE F&O bhavcopy (UDiFF) via nsearchives.nseindia.com",
                "strikes": "same bhavcopy, nearest expiry, ATM ± 8 strikes; max pain computed over the full chain",
                "index": "NIFTY 50 closes from eod2_data daily/nifty 50.csv (market adjustment for the scoreboard)",
            },
            "thresholds": {"volume_above": 1.0, "pcr_low": 0.7, "pcr_high": 1.3, "volume_window_days": 20},
            "index_closes": index,
            "disclaimer": DISCLAIMER,
        },
        "summary": {
            "bullish": counts.get(BULLISH, 0), "bearish": counts.get(BEARISH, 0),
            "neutral": counts.get(NEUTRAL, 0), "unclassified": counts.get(UNCLASSIFIED, 0),
        },
        "stocks": stocks,
    }
    scan["meta"]["commentary"] = generate_commentary(scan) if commentary else None
    return scan


def render(scan: dict, template: Path, out: Path) -> None:
    html = template.read_text(encoding="utf-8")
    payload = json.dumps(scan, separators=(",", ":")).replace("</", "<\\/")
    if "/*__SCAN_DATA__*/" not in html:
        raise ValueError("template is missing the /*__SCAN_DATA__*/ placeholder")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html.replace("/*__SCAN_DATA__*/", payload), encoding="utf-8")


def _fo_warnings(stocks: list[dict], fo_status: str, chain_status: str, chain_problems: dict[str, str]) -> list[dict]:
    """Per-stock data gaps, so a gap is shown on that stock instead of failing the build."""
    warnings: list[dict] = []
    if fo_status == "ok":
        for st in stocks:
            if st.get("oi_change_pct") is None:
                warnings.append({"symbol": st["symbol"], "stage": "oi", "reason": "no futures OI rows in the bhavcopy"})
            elif st.get("pcr") is None:
                warnings.append({"symbol": st["symbol"], "stage": "pcr", "reason": "no call OI, PCR undefined"})
    if chain_status == "ok":
        for sym, why in sorted(chain_problems.items()):
            warnings.append({"symbol": sym, "stage": "chain", "reason": why})
        for st in stocks:
            c = st.get("chain")
            if c and c.get("one_sided_strikes"):
                warnings.append({"symbol": st["symbol"], "stage": "chain",
                                 "reason": f"{c['one_sided_strikes']} strike(s) listed on one side only; shown with 0 OI on the missing side"})
    return warnings


def _int(v):
    return None if v is None or pd.isna(v) else int(v)


def _round(v, nd=2):
    return None if v is None or pd.isna(v) else round(float(v), nd)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the F&O EOD scan page")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2",
                    help="folder of eod2 daily CSVs (missing symbols are fetched from GitHub)")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    ap.add_argument("--template", type=Path, default=ROOT / "templates" / "index.html")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "index.html")
    ap.add_argument("--json", type=Path, default=ROOT / "data" / "scan.json")
    ap.add_argument("--skip-fo", action="store_true", help="do not contact NSE for the F&O bhavcopy")
    ap.add_argument("--commentary", action="store_true",
                    help="add a plain-English, descriptive read-out of the scan via the Anthropic API (needs ANTHROPIC_API_KEY)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")

    scan = build(args.eod2_dir, args.cache_dir, skip_fo=args.skip_fo, commentary=args.commentary)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(scan, indent=1), encoding="utf-8")
    render(scan, args.template, args.out)
    s, m = scan["summary"], scan["meta"]
    print(f"as of {m['as_of']}: {s['bullish']} bullish, {s['bearish']} bearish, {s['neutral']} neutral, "
          f"{s['unclassified']} unclassified | OI/PCR: {m['fo_status']} | strike tables: {m['chain_status']} | wrote {args.out}")
    for w in m["fo_warnings"]:
        print(f"  note {w['symbol']}: [{w['stage']}] {w['reason']}")


if __name__ == "__main__":
    main()
