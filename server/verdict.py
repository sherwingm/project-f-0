"""Evidence verdict for one stock: the scan's numbers plus recent news, weighed into a structured
assessment by Claude with web search.

Output (JSON): lean (bullish | bearish | mixed), confidence (low | medium | high), a one-line
data read, the news items it found (headline, date, source, url, direction), the reasoning, the
main risks, and what would change the verdict. It is an assessment of evidence for the reader's
own judgement. The brief forbids instructions (buy/sell/enter/exit/hold, strikes, targets,
stops) and price prediction; a regex post-check rejects any output that contains them and the
endpoint then returns a deterministic verdict built from the label alone, marked as such.
Results are cached per symbol per scan date (news changes intraday, so a "refresh" flag
bypasses the cache). Web search costs a few cents per call; keep MAX_USES small.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from server.commentary import FORBIDDEN

log = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))

SYSTEM = """You are an equity-derivatives analyst producing an EVIDENCE VERDICT for one NSE stock,
for a reader who will make their own decisions. You get the stock's end-of-day derivatives numbers
(price change, volume vs 20-day average, futures open interest change, put-call ratio, the
scanner's descriptive label and the rules behind it) and, when available, live intraday numbers.
Use web search (at most 5 searches) to find material news about the company from the last 10 days:
results, guidance, orders, regulatory or legal actions, management changes, block deals, index
changes, sector news, analyst rating changes. Weigh the data and the news together.

Respond with ONLY a JSON object, no prose before or after, no markdown fences:
{"lean": "bullish|bearish|mixed", "confidence": "low|medium|high",
 "data_read": "<one sentence: what the derivatives numbers show, with the numbers>",
 "news": [{"headline": "...", "date": "YYYY-MM-DD", "source": "...", "url": "...", "direction": "+|-|0", "why": "<one clause>"}],
 "reasoning": "<3-5 sentences weighing data against news; name what is strong and what is weak>",
 "risks": "<2-3 sentences on what could make this read wrong>",
 "would_change": "<one sentence: the specific data or event that would flip the lean>"}

Rules: "lean" is about the balance of evidence, not a forecast or an instruction. Never tell the
reader to buy, sell, enter, exit, hold, add, short, go long, or which strike, target or stop to use.
Never predict a price level or use "will rise/fall". If you find no material news, return an empty
news list, say so in reasoning, and set confidence to "low". Cite only news you actually found;
include the URL. Dates in YYYY-MM-DD."""

MAX_USES = 5


def deterministic_verdict(stock: dict, reason: str) -> dict:
    lean = {"Bullish setup": "bullish", "Bearish setup": "bearish"}.get(stock.get("label"), "mixed")
    return {"lean": lean, "confidence": "low",
            "data_read": "; ".join(stock.get("reasons", [])),
            "news": [], "reasoning": f"Data-only verdict: {reason}. The lean repeats the scanner's label and adds nothing from news.",
            "risks": "A data-only read ignores results, orders, regulatory actions and sector moves that can dominate a single session.",
            "would_change": "Any material company news.", "deterministic": True}


class Verdict:
    def __init__(self, api_key: str, model: str, cache_dir: Path):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def _cache_file(self, as_of: str) -> Path:
        return self.cache_dir / f"verdict_{as_of}.json"

    def get(self, stock: dict, as_of: str, thresholds: dict, live: dict | None = None, refresh: bool = False) -> dict:
        f = self._cache_file(as_of)
        with self.lock:
            cache = json.loads(f.read_text()) if f.exists() else {}
            if not refresh and stock["symbol"] in cache:
                return cache[stock["symbol"]]
        result = self._generate(stock, as_of, thresholds, live)
        if not result.get("deterministic"):          # fallbacks are not cached, so the next tap retries
            with self.lock:
                cache = json.loads(f.read_text()) if f.exists() else {}
                cache[stock["symbol"]] = result
                f.write_text(json.dumps(cache, indent=1))
        return result

    def _prompt(self, stock: dict, as_of: str, thresholds: dict, live: dict | None) -> str:
        v = lambda x, fmt: "n/a" if x is None else fmt.format(x)  # noqa: E731
        lines = [f"Stock: {stock['symbol']} (NSE). Session: {as_of}. Today: {datetime.now(IST).strftime('%Y-%m-%d')}.",
                 f"Close ₹{stock.get('close')} ({v(stock.get('price_change_pct'), '{:+.2f}%')} vs previous close ₹{stock.get('prev_close')}).",
                 f"Volume {v(stock.get('volume_ratio'), '{:.2f}x')} its 20-day average.",
                 f"Futures OI {v(stock.get('fut_oi'), '{:,}')} ({v(stock.get('oi_change_pct'), '{:+.2f}%')} vs previous session).",
                 f"PCR {v(stock.get('pcr'), '{:.2f}')} (put OI {v(stock.get('put_oi'), '{:,}')}, call OI {v(stock.get('call_oi'), '{:,}')}).",
                 f"Scanner label: {stock.get('label')}. Reasons: {'; '.join(stock.get('reasons', []))}.",
                 f"Label rules: price up/down + volume above average + futures OI rising; PCR < {thresholds.get('pcr_low', 0.7)} read as bullish sentiment, > {thresholds.get('pcr_high', 1.3)} bearish, secondary only."]
        c = stock.get("chain")
        if c:
            lines.append(f"Nearest expiry {c.get('expiry')}: highest call OI at {c.get('max_call_oi_strike')}, highest put OI at {c.get('max_put_oi_strike')}, max pain {c.get('max_pain')}.")
        if live:
            lines.append(f"Live now: ₹{live.get('ltp')} ({v(live.get('chg_pct'), '{:+.2f}%')} today), futures OI {v(live.get('fut_oi'), '{:,}')} ({v(live.get('fut_oi_chg_pct'), '{:+.2f}%')} vs close), live PCR {v(live.get('live_pcr'), '{:.2f}')}.")
        lines.append("Search for material news on this company from the last 10 days, then give the verdict JSON.")
        return "\n".join(lines)

    def _generate(self, stock: dict, as_of: str, thresholds: dict, live: dict | None) -> dict:
        try:
            msg = self.client.messages.create(
                model=self.model, max_tokens=1500, system=SYSTEM,
                tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_USES}],
                messages=[{"role": "user", "content": self._prompt(stock, as_of, thresholds, live)}])
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        except Exception as exc:  # noqa: BLE001
            log.error("verdict %s: %s", stock["symbol"], exc)
            return deterministic_verdict(stock, f"model call failed ({type(exc).__name__})")
        data = _parse_json(text)
        if not data:
            return deterministic_verdict(stock, "model returned no parseable verdict")
        flat = " ".join(str(data.get(k, "")) for k in ("data_read", "reasoning", "risks", "would_change"))
        hit = FORBIDDEN.search(flat)
        if hit:
            log.warning("verdict %s dropped: instruction-like language (%r)", stock["symbol"], hit.group(0))
            return deterministic_verdict(stock, "model output contained trading-instruction language and was discarded")
        out = {"lean": data.get("lean") if data.get("lean") in ("bullish", "bearish", "mixed") else "mixed",
               "confidence": data.get("confidence") if data.get("confidence") in ("low", "medium", "high") else "low",
               "data_read": str(data.get("data_read", "")), "reasoning": str(data.get("reasoning", "")),
               "risks": str(data.get("risks", "")), "would_change": str(data.get("would_change", "")),
               "news": [n for n in (data.get("news") or []) if isinstance(n, dict) and n.get("headline")][:8],
               "generated_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M"), "deterministic": False}
        return out


def _parse_json(text: str) -> dict | None:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None
