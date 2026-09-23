"""Plain-language reading of one stock's scan row, written by Claude from the numbers only.

The model is given the row's numbers, the label rules, and a fixed brief: explain what the
data shows, the conventional interpretation, what would confirm or contradict the pattern, and
the main risk — in under 130 words. It is not allowed to tell the reader to buy, sell, enter,
exit, hold, or which strike to trade, and it may not predict price. A post-check rejects any
output that slips into those forms and falls back to a deterministic summary, so the commentary
stays descriptive even if the model misbehaves. Results are cached per symbol per scan date.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path

log = logging.getLogger(__name__)

SYSTEM = """You write short plain-language readings of end-of-day NSE derivatives data for one stock.
You are describing data to a reader who will make their own decisions. Rules:
- Explain what each number shows and the conventional interpretation of the combination (long/short buildup, unwinding, options positioning).
- Say what would confirm the pattern and what would contradict it, using the numbers.
- State the main risk in one sentence.
- Never instruct the reader: no buy, sell, enter, exit, hold, add, book, short, go long, target, stop-loss, or which strike or contract to trade.
- Never predict where price will go. Do not use "will", "likely to rise/fall", "expect".
- Plain sentences, no headings, no bullet points, 90 to 130 words. Refer to the stock by symbol."""

# Imperative/predictive phrasings we refuse to pass through.
FORBIDDEN = re.compile(
    r"\b(buy|sell|go long|go short|short it|short (?:the|this|that) stock|enter|exit|hold|book profit|"
    r"accumulate|add on dips|should (?:buy|sell|trade|short|go long|enter|exit)|recommend\w*|"
    r"likely to (?:rise|fall|move|go|break)|will (?:rise|fall|rally|drop|break|move|go)|expect(?:ed)? to|"
    r"(?:target|stop[- ]?loss) (?:of|at) ?₹?\d)\b", re.I)
# "short buildup", "short covering", "sellers", "buying" are descriptive market terms and pass;
# only instruction forms (buy, sell, go short, enter, exit, hold, a target/stop at a price) are refused.


def deterministic_summary(stock: dict) -> str:
    r = "; ".join(stock.get("reasons", []))
    return f"{stock['symbol']} closed at ₹{stock['close']} ({stock['price_change_pct']:+.2f}%). {r}."


class Commentary:
    def __init__(self, api_key: str, model: str, cache_dir: Path):
        self.api_key, self.model = api_key, model
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self._client = None

    def client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def _cache_file(self, as_of: str) -> Path:
        return self.cache_dir / f"commentary_{as_of}.json"

    def get(self, stock: dict, as_of: str, thresholds: dict) -> dict:
        f = self._cache_file(as_of)
        with self.lock:
            cache = json.loads(f.read_text()) if f.exists() else {}
        if stock["symbol"] in cache:
            return cache[stock["symbol"]]
        result = self.generate(stock, thresholds)
        result["as_of"] = as_of
        with self.lock:
            cache = json.loads(f.read_text()) if f.exists() else {}
            cache[stock["symbol"]] = result
            f.write_text(json.dumps(cache, indent=1))
        return result

    def generate(self, stock: dict, thresholds: dict) -> dict:
        facts = {k: stock.get(k) for k in ("symbol", "date", "close", "prev_close", "price_change_pct", "volume", "avg_volume_20d",
                                            "volume_ratio", "fut_oi", "fut_oi_prev", "oi_change_pct", "call_oi", "put_oi", "pcr",
                                            "label", "reasons")}
        chain = stock.get("chain") or {}
        facts["nearest_expiry_levels"] = {k: chain.get(k) for k in ("expiry", "atm", "max_call_oi_strike", "max_put_oi_strike", "max_pain")}
        user = ("Data (JSON):\n" + json.dumps(facts, indent=1) + "\n\nLabel rules: " + json.dumps(thresholds) +
                "\nWrite the reading now.")
        text, model_used = None, None
        for attempt in range(2):
            try:
                msg = self.client().messages.create(model=self.model, max_tokens=400, system=SYSTEM,
                                                    messages=[{"role": "user", "content": user}])
                candidate = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
                if not FORBIDDEN.search(candidate):
                    text, model_used = candidate, self.model
                    break
                log.warning("commentary for %s used a forbidden phrasing (attempt %d); retrying", stock["symbol"], attempt + 1)
                user += "\n\nYour previous answer contained an instruction or prediction. Rewrite it purely descriptively."
            except Exception as exc:  # noqa: BLE001
                log.error("commentary API error for %s: %s", stock["symbol"], exc)
                break
        if text is None:
            return {"text": deterministic_summary(stock), "model": "deterministic-fallback", "ai": False}
        return {"text": text, "model": model_used, "ai": True}
