"""Write the result tables to data/results/ (numbers only). Every CSV has a header row and a companion .md next
to it that explains each column in one line.

    python -m scanner.results_export --since 2023-01-01                    # all four parts
    python -m scanner.results_export --since 2023-01-01 --only labels      # labels | cheap | events | model

labels   labels_detail.csv, labels_summary.csv      scanner.backtest_labels on every cached bhavcopy session
cheap    cheap_options_detail.csv, cheap_options_summary.csv   scanner.backtest_cheap_options
events   event_study.csv                            scanner.event_study summary over the event store
model    model_folds.csv                            scanner.model walk-forward (retrains data/model.pkl)

Nothing is interpreted. The summary tables are also printed.
"""
from __future__ import annotations

import argparse
import logging
import re
from datetime import date
from pathlib import Path

import pandas as pd

from server import charges as ch

from .binomial import hits_needed
from .build import ROOT

log = logging.getLogger("results_export")
OUT_DIR = ROOT / "data" / "results"
THRESHOLDS = (0.5, 1.0, 2.0)
DETAIL_THRESHOLD = 1.0                    # the page's default; labels_detail's scored/hit columns use it
PARTS = ("labels", "cheap", "events", "model")

DOCS: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "labels_detail": ("One row per stock-day on every session with a cached F&O bhavcopy (scanner.backtest_labels).", [
        ("date", "session the label was computed for (YYYY-MM-DD)"),
        ("symbol", "NSE symbol (today's F&O universe)"),
        ("label", "scanner label that day: Bullish setup, Bearish setup, Neutral or Unclassified"),
        ("price_change_pct", "close vs previous close, % (eod2)"),
        ("volume_ratio", "volume / average of the 20 sessions before (eod2)"),
        ("oi_change_pct", "futures OI change %, all expiries (bhavcopy)"),
        ("pcr", "put OI / call OI over all stock options (bhavcopy)"),
        ("fwd3_return", "stock return from this close to the close 3 sessions later, %"),
        ("nifty_fwd3_return", "NIFTY 50 return over the same 3 sessions, %"),
        ("adj_fwd3_return", "fwd3_return minus nifty_fwd3_return (market-adjusted), %"),
        ("scored", f"Y when the row counts as a scored call at the {DETAIL_THRESHOLD:g}% threshold, else N"),
        ("scored_reason", "why not scored: dup (within 3 sessions of the stock's previous scored call), small "
                          f"(|adj_fwd3_return| <= {DETAIL_THRESHOLD:g}%), pending (no forward data), neutral, unclassified"),
        ("hit", "Y when scored and the move went the label's way, N when scored and it did not, blank otherwise"),
    ]),
    "labels_summary": ("Two kinds of row. hit_rate rows: per label x threshold, scored by the page's scoreboard rules; "
                       "base = Neutral stock-days scored the same way in the same direction. returns rows: per label x "
                       "horizon, market-adjusted returns (stock minus NIFTY 50) against Neutral over the same horizon, "
                       "one stock-day per stock per horizon (non-overlapping windows). Columns that do not apply to a "
                       "row type are blank.", [
        ("row_type", "hit_rate or returns"),
        ("label", "Bullish setup (scored as bullish) or Bearish setup (scored as bearish)"),
        ("threshold_pct", "hit_rate rows: a call is scored only when |adj_fwd3_return| exceeds this, %"),
        ("horizon_sessions", "sessions ahead the return is measured over (3 on hit_rate rows)"),
        ("stock_days", "stock-days with this label"),
        ("scored_n", "hit_rate rows: calls scored (not dup, small or pending)"),
        ("hits", "hit_rate rows: scored calls where the move went the label's way"),
        ("hit_pct", "hit_rate rows: hits / scored_n x 100"),
        ("base_n", "hit_rate rows: Neutral stock-days scored in the same direction at the same threshold"),
        ("base_hit_pct", "hit_rate rows: hit % of those Neutral stock-days"),
        ("diff_pts", "hit_rate rows: hit_pct minus base_hit_pct, percentage points"),
        ("z_vs_base", "hit_rate rows: two-proportion z of hit_pct vs base_hit_pct (pooled standard error)"),
        ("z_vs_base_clustered", "hit_rate rows: the same difference as a t with standard errors clustered by date"),
        ("needs_vs_coin", "hit_rate rows: hits needed at scored_n to beat a coin (N/2 + 1.645 x sqrt(N)/2)"),
        ("n_returns", "returns rows: stock-days used (one per stock per horizon_sessions)"),
        ("mean_adj_return", "returns rows: mean market-adjusted return over horizon_sessions, %"),
        ("median_adj_return", "returns rows: median market-adjusted return, %"),
        ("t_mean", "returns rows: t-statistic of mean_adj_return against zero"),
        ("base_n_returns", "returns rows: Neutral stock-days used, same rule"),
        ("base_mean_adj_return", "returns rows: Neutral mean market-adjusted return, %"),
        ("base_median_adj_return", "returns rows: Neutral median market-adjusted return, %"),
        ("base_t_mean", "returns rows: t-statistic of the Neutral mean against zero"),
        ("diff_mean", "returns rows: mean_adj_return minus base_mean_adj_return, percentage points"),
        ("welch_t_vs_base", "returns rows: Welch's t of the difference in means"),
        ("t_mean_clustered", "returns rows: t of mean_adj_return, standard error clustered by date"),
        ("base_t_mean_clustered", "returns rows: t of the Neutral mean, clustered by date"),
        ("diff_t_clustered", "returns rows: t of diff_mean, clustered by date (dates shared by both groups)"),
    ]),
    "cheap_options_detail": ("One row per cheap stock option tested (ClsPric <= Rs 2, 3-7 sessions to expiry), one lot "
                             "bought at the close + 1 tick (scanner.backtest_cheap_options).", [
        ("date", "session the option was bought"),
        ("symbol", "underlying NSE symbol"),
        ("contract", "SYMBOL + YY + MON + strike + CE/PE"),
        ("type", "CE or PE"),
        ("strike", "strike price, Rs"),
        ("expiry", "expiry date"),
        ("premium", "option close that day (ClsPric), Rs"),
        ("spot", "underlying price that day (UndrlygPric; blank before 2024-07-05, when NSE's file had none)"),
        ("sessions_to_expiry", "sessions after the buy date up to and including expiry"),
        ("lot", "lot size used (the file's; before 2024-07-05 today's lot size, as the old file had none)"),
        ("label", "scanner label on the underlying that day"),
        ("fill_price", "premium + 1 tick (0.05), Rs per unit"),
        ("exit_3s_price", "option close 3 sessions later - 1 tick, floored at 0, Rs per unit"),
        ("exit_expiry_value", "intrinsic value at expiry from the underlying's expiry-day close, Rs per unit"),
        ("charges", "buy leg + 3-session sell leg charges, Rs per lot (server/charges.py)"),
        ("charges_expiry", "buy leg charges + exercise STT when held to expiry, Rs per lot"),
        ("net_3s", "sell proceeds after charges - cost including charges, Rs per lot"),
        ("net_expiry", "intrinsic value after exercise STT - cost including charges, Rs per lot"),
        ("multiple_3s", "sell proceeds after charges / cost including charges"),
        ("multiple_expiry", "value at expiry after STT / cost including charges"),
        ("excluded", "blank, or why the row is left out of the summary: below_intrinsic (close below intrinsic value "
                     "on the buy date by > 1% of spot: a stale print), contract_changed (the contract is gone on its "
                     "expiry day: strikes adjusted), price_adjusted (raw future move vs eod2's adjusted move differs "
                     "by > 3%: a bonus, split or demerger in the window)"),
    ]),
    "cheap_options_summary": ("The backtest's summary table by group, both exit rules; rows flagged "
                              "in cheap_options_detail.excluded are left out.", [
        ("exit_rule", "3s = sold at the close 3 sessions later; expiry = held to expiry"),
        ("group", "the subset of contracts"),
        ("n", "contracts in the group with an outcome"),
        ("wins", "contracts with net > 0"),
        ("pct_net_positive", "wins / n x 100"),
        ("mean_multiple", "mean of payoff / cost"),
        ("median_multiple", "median of payoff / cost"),
        ("best_multiple", "largest payoff / cost"),
        ("worst_multiple", "smallest payoff / cost"),
        ("net_per_1000", "total net / total cost x 1,000: net Rs per Rs 1,000 risked"),
        ("needs_vs_coin", "wins needed at n to beat a coin"),
        ("clears_coin", "Y when wins >= needs_vs_coin"),
    ]),
    "event_study": ("Market-adjusted returns (stock minus NIFTY 50, close to close, %) around each stored tier-1/2 "
                    "event, per type / subtype / bucket (scanner.event_study).", [
        ("group", "type, 'type / subtype' or 'type [bucket]' as printed by the study"),
        ("type", "event type"),
        ("subtype", "subtype, blank on type and bucket rows"),
        ("bucket", "materiality bucket, blank on type and subtype rows"),
        ("n", "events in the group"),
        ("pre_mean", "mean CAR, close T-5 -> close T-1"),
        ("pre_median", "median CAR, close T-5 -> close T-1"),
        ("pre_pos_pct", "share of events with pre CAR > 0, %"),
        ("pre_t", "t-statistic of pre_mean"),
        ("pre_tc", "t of pre_mean with standard errors clustered by event date"),
        ("day_mean", "mean CAR, close T-1 -> close T"),
        ("day_median", "median CAR, close T-1 -> close T"),
        ("day_pos_pct", "share with day CAR > 0, %"),
        ("day_t", "t-statistic of day_mean"),
        ("day_tc", "t of day_mean clustered by event date"),
        ("post_mean", "mean CAR, close T+1 -> close T+5"),
        ("post_median", "median CAR, close T+1 -> close T+5"),
        ("post_pos_pct", "share with post CAR > 0, %"),
        ("post_t", "t-statistic of post_mean"),
        ("post_tc", "t of post_mean clustered by event date"),
    ]),
    "model_folds": ("Walk-forward folds of the NSE model (train on every earlier quarter, test on the next), plus "
                    "an OVERALL row over all test rows (scanner.model).", [
        ("fold", "test quarter, or OVERALL"),
        ("train_end", "last day in the training data"),
        ("test_start", "first day tested"),
        ("test_end", "last day tested"),
        ("n", "stock-days tested"),
        ("accuracy", "share of test rows whose most likely class was the outcome"),
        ("brier", "multi-class Brier score of the model's probabilities (0 best, 2 worst)"),
        ("base_brier", "Brier score of the base rate: the training class shares forecast for every row"),
        ("top_decile_hit_up", "share 'up' among the 10% of test rows with the highest p_up"),
        ("top_decile_base_up", "share 'up' among all test rows"),
        ("top_decile_hit_down", "share 'down' among the 10% of test rows with the highest p_down"),
        ("top_decile_base_down", "share 'down' among all test rows"),
    ]),
}


def write(df: pd.DataFrame, name: str, out_dir: Path) -> Path:
    """<name>.csv with exactly the documented columns, in order, and <name>.md explaining each."""
    title, cols = DOCS[name]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.csv"
    df[[c for c, _ in cols]].to_csv(path, index=False)
    md = [f"# {name}.csv", "", title, "", *(f"- `{c}`: {doc}" for c, doc in cols), ""]
    (out_dir / f"{name}.md").write_text("\n".join(md), encoding="utf-8")
    log.info("%s: %d rows", path, len(df))
    return path


# ---------------------------------------------------------------- labels
def labels_tables(df: pd.DataFrame, cal: list[date]) -> tuple[pd.DataFrame, pd.DataFrame]:
    from .backtest_labels import annotate, versus_base
    from .backtest_labels import returns_vs_base
    detail = annotate(df, cal, DETAIL_THRESHOLD).rename(columns={
        "fwd_return": "fwd3_return", "nifty_fwd_return": "nifty_fwd3_return", "move": "adj_fwd3_return"})
    hits = pd.DataFrame(versus_base(df, cal, THRESHOLDS)).assign(row_type="hit_rate", horizon_sessions=3)
    rets = pd.DataFrame(returns_vs_base(df, cal)).assign(row_type="returns")
    return detail, pd.concat([hits, rets], ignore_index=True)


def run_labels(since: date, out_dir: Path, eod2_dir: Path, cache_dir: Path) -> pd.DataFrame:
    from .backtest_cheap_options import _read_index
    from .backtest_labels import run
    from .equity import load_symbol
    from .nse_fo import download_fo_bhavcopy
    from .universe import fetch_fo_lots
    index = _read_index(eod2_dir)["Close"]
    cal = [t.date() for t in index.index]
    in_cal = set(cal)
    days = sorted(d for d in (date.fromisoformat(f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}")
                              for p in cache_dir.glob("fo_bhavcopy_*.csv")) if d >= since and d in in_cal)
    symbols = sorted(fetch_fo_lots(cache_path=cache_dir / "fo_universe.txt"))

    def equity(sym):
        try:
            return load_symbol(sym, eod2_dir)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: no eod2 data (%s)", sym, exc)
            return None

    df = run(days, cal, lambda d: download_fo_bhavcopy(d, cache_dir=cache_dir), equity, symbols, index, 3)
    detail, summary = labels_tables(df, cal)
    write(detail, "labels_detail", out_dir)
    write(summary, "labels_summary", out_dir)
    return summary


# ---------------------------------------------------------------- cheap options
def cheap_tables(df: pd.DataFrame, tick: float = 0.05) -> tuple[pd.DataFrame, pd.DataFrame]:
    from .backtest_cheap_options import OUTCOMES, summarise
    d = df.copy()
    buy = [ch.leg(t, "BUY", int(l), float(e))["total"] for t, l, e in zip(d["type"], d["lot"], d["entry_price"])]
    sell_px = (d["exit_close"] - tick).clip(lower=0).round(2)
    sell = [ch.leg(t, "SELL", int(l), float(p))["total"] if pd.notna(p) and p > 0 else (0.0 if pd.notna(p) else None)
            for t, l, p in zip(d["type"], d["lot"], sell_px)]
    stt = [ch.exercise(int(l), float(v))["total"] if pd.notna(v) else None for l, v in zip(d["lot"], d["intrinsic"])]
    d["fill_price"], d["exit_3s_price"], d["exit_expiry_value"] = d["entry_price"], sell_px, d["intrinsic"]
    d["charges"] = [round(b + s, 2) if s is not None else None for b, s in zip(buy, sell)]
    d["charges_expiry"] = [round(b + x, 2) if x is not None else None for b, x in zip(buy, stt)]
    d = d.rename(columns={"dte": "sessions_to_expiry", "exit_net": "net_3s", "expiry_net": "net_expiry",
                          "exit_multiple": "multiple_3s", "expiry_multiple": "multiple_expiry"})
    rows = []
    for key, _ in OUTCOMES:
        for r in summarise(df, (3, 7))[key]:
            need = hits_needed(r["count"])
            rows.append({"exit_rule": "3s" if key == "exit" else "expiry", "group": r["group"], "n": r["count"],
                         "wins": r["wins"], "pct_net_positive": r["pct_positive"], "mean_multiple": r["mean_multiple"],
                         "median_multiple": r["median_multiple"], "best_multiple": r["best_multiple"],
                         "worst_multiple": r["worst_multiple"], "net_per_1000": r["net_per_1000"],
                         "needs_vs_coin": need, "clears_coin": ("Y" if r["wins"] >= need else "N") if need else ""})
    return d, pd.DataFrame(rows)


def run_cheap(since: date, out_dir: Path, eod2_dir: Path, cache_dir: Path) -> pd.DataFrame:
    from .backtest_cheap_options import Inputs, NseInputs, run
    inp = NseInputs(eod2_dir, cache_dir)
    df = run(Inputs(inp.sessions, inp.bhav, inp.equity, inp.lots), since, inp.eod2_last, 2.0, (3, 7), 3)
    detail, summary = cheap_tables(df)
    write(detail, "cheap_options_detail", out_dir)
    write(summary, "cheap_options_summary", out_dir)
    return summary


# ---------------------------------------------------------------- events
def event_table(summary: pd.DataFrame) -> pd.DataFrame:
    s = summary.copy()
    parsed = [re.match(r"^(?P<type>[a-z_]+)(?: / (?P<sub>.+?))?(?: \[(?P<bucket>[^\]]+)\])?$", g) for g in s["group"]]
    s["type"] = [m.group("type") if m else g.split(" ")[0] for m, g in zip(parsed, s["group"])]
    s["subtype"] = [(m.group("sub") or "") if m else g.split(" / ", 1)[-1] for m, g in zip(parsed, s["group"])]
    s["bucket"] = [(m.group("bucket") or "") if m else "" for m in parsed]
    return s.rename(columns={"count": "n"})


def run_events(since: date, out_dir: Path, eod2_dir: Path) -> pd.DataFrame:
    from .equity import load_symbol
    from .event_study import load_index, study, summarise
    from .events.store import Store
    with Store() as store:
        events = [e for e in store.events_between(since, date.today(), max_tier=2) if e["bucket"] != "ignore"]
    index = load_index(eod2_dir)
    closes = {}
    for sym in sorted({e["symbol"] for e in events}):
        try:
            closes[sym] = load_symbol(sym, eod2_dir)["Close"]
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: no eod2 closes (%s)", sym, exc)
    table = event_table(summarise(study(events, closes, index)))
    write(table, "event_study", out_dir)
    return table


# ---------------------------------------------------------------- model
def folds_table(report: dict) -> pd.DataFrame:
    rows = []
    for f in report["folds"] + [{**report["overall"], "quarter": "OVERALL", "test_rows": sum(x["test_rows"] for x in report["folds"]),
                                 "train_end": report["folds"][-1].get("train_end"),
                                 "test_start": report["folds"][0].get("test_start"),
                                 "test_end": report["folds"][-1].get("test_end")}]:
        td = f.get("top_decile") or {}
        rows.append({"fold": f["quarter"], "train_end": f.get("train_end"), "test_start": f.get("test_start"),
                     "test_end": f.get("test_end"), "n": f["test_rows"], "accuracy": f["accuracy"], "brier": f["brier"],
                     "base_brier": f.get("base_brier"),
                     "top_decile_hit_up": (td.get("up") or {}).get("hit_rate"),
                     "top_decile_base_up": (td.get("up") or {}).get("base_rate"),
                     "top_decile_hit_down": (td.get("down") or {}).get("hit_rate"),
                     "top_decile_base_down": (td.get("down") or {}).get("base_rate")})
    return pd.DataFrame(rows)


def run_model(since: date, out_dir: Path) -> pd.DataFrame:
    from .model import train
    table = folds_table(train(since))
    write(table, "model_folds", out_dir)
    return table


def main() -> None:
    ap = argparse.ArgumentParser(description="write the result tables to data/results/ (numbers only)")
    ap.add_argument("--since", type=date.fromisoformat, default=date(2023, 1, 1))
    ap.add_argument("--only", nargs="+", choices=PARTS, default=list(PARTS))
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.max_rows", 500)
    if "labels" in a.only:
        print(run_labels(a.since, a.out_dir, a.eod2_dir, a.cache_dir).to_string(index=False))
    if "cheap" in a.only:
        print(run_cheap(a.since, a.out_dir, a.eod2_dir, a.cache_dir).to_string(index=False))
    if "events" in a.only:
        t = run_events(a.since, a.out_dir, a.eod2_dir)
        print(t[[c for c, _ in DOCS["event_study"][1]]].to_string(index=False))
    if "model" in a.only:
        print(run_model(a.since, a.out_dir).to_string(index=False))


if __name__ == "__main__":
    main()
