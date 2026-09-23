"""Runtime configuration. Everything defaults to the safe setting: paper trading, no broker,
no live feed, no commentary, and password-protected access.

    APP_PASSWORD          required; the page and API sit behind HTTP Basic auth (user: "user")
    DATA_PROVIDER         none | upstox | groww | kite | fake   (default: same as BROKER)
                          where live quotes come from; upstox is read-only and free (Analytics Token)
    KOTAK_CONSUMER_KEY    Kotak Neo: Neo app → More → Trade API → Generate application (enough for live data)
    KOTAK_MOBILE, KOTAK_UCC, KOTAK_TOTP_SECRET, KOTAK_MPIN   only for real orders through Kotak
    KOTAK_CHAIN_CALLS_PER_POLL  option-chain calls per poll for live PCR/strike OI (default 12)
    UPSTOX_ANALYTICS_TOKEN  1-year read-only token from account.upstox.com/developer/apps → Analytics
    UPSTOX_CHAIN_CALLS_PER_POLL  option-chain calls per poll for live PCR/strike OI (default 12)
    ORDERS                true | false   (default false: the page has no order controls at all)
    BROKER                none | kite | groww | fake   (default none; only used when ORDERS=true)
    PAPER                 true | false           (default true: orders are simulated and logged)
    KITE_API_KEY, KITE_API_SECRET, KITE_ACCESS_TOKEN
                          Kite Connect (paid plan needed for quotes; Personal plan can only trade)
    GROWW_TOTP_TOKEN, GROWW_TOTP_SECRET   Groww TOTP-flow key (headless daily login), or
    GROWW_ACCESS_TOKEN                    a token pasted from the Groww Cloud API Keys page
    GROWW_OI_CALLS_PER_POLL               single-contract quote calls per poll for futures OI (default 60)
    POLL_SECONDS          live quote poll interval during market hours (default 30)
    ANTHROPIC_API_KEY     enables the plain-language commentary endpoint
    COMMENTARY_MODEL      default claude-sonnet-4-6
    MAX_LOTS_PER_ORDER    default 5
    MAX_ORDERS_PER_DAY    default 20
    DATA_DIR              default ./data

  Paper engine (guide 12)
    CHARGES_JSON          JSON object overriding any rate in server/charges.py, e.g. {"OPT_NSE_PER_LAKH": 35.03}
    LIQ_FUT_ACCEPT_SPREAD_PCT 0.05   LIQ_FUT_REFUSE_SPREAD_PCT 0.15   futures spread bands, % of mid
    LIQ_FUT_ACCEPT_DEPTH_PCT  25     LIQ_FUT_REFUSE_DEPTH_PCT  50     order qty as % of visible depth
    LIQ_OPT_ACCEPT_SPREAD_PCT 3      LIQ_OPT_REFUSE_SPREAD_PCT 8      options spread bands, % of mid
    LIQ_OPT_ACCEPT_DEPTH_PCT  20     LIQ_OPT_REFUSE_DEPTH_PCT  100    order qty as % of visible depth
    LIQ_OPT_MIN_OI_LOTS       50                                      strike OI floor for options
    LOTTERY_MAX_PREMIUM       2      LOTTERY_MAX_SESSIONS      2      cheap / near-expiry bucket
    FILL_TICK             0.05   tick size for fills (one tick of latency, rounding against the order)
    PAPER_QUEUE_FILL_AT   09:20  market-closed paper orders fill at the first poll at/after this IST time
    NSE_HOLIDAYS          comma-separated YYYY-MM-DD trading holidays (sessions are weekdays minus these)
    PAPER_CAPITAL         500000   starting capital of the paper account (data/paper_ledger.json keeps its own once created)
    MARGIN_ESTIMATE_PCT   18       margin estimate: % of notional for futures / short options (long options: the premium)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    app_password: str = os.getenv("APP_PASSWORD", "")
    broker: str = os.getenv("BROKER", "none").lower()
    data_provider: str = os.getenv("DATA_PROVIDER", os.getenv("BROKER", "none")).lower()
    orders: bool = _bool("ORDERS", False)
    paper: bool = _bool("PAPER", True)
    kotak_consumer_key: str = os.getenv("KOTAK_CONSUMER_KEY", "")
    kotak_mobile: str = os.getenv("KOTAK_MOBILE", "")
    kotak_ucc: str = os.getenv("KOTAK_UCC", "")
    kotak_totp_secret: str = os.getenv("KOTAK_TOTP_SECRET", "")
    kotak_mpin: str = os.getenv("KOTAK_MPIN", "")
    kotak_chain_calls_per_poll: int = int(os.getenv("KOTAK_CHAIN_CALLS_PER_POLL", "12"))
    upstox_analytics_token: str = os.getenv("UPSTOX_ANALYTICS_TOKEN", "")
    upstox_chain_calls_per_poll: int = int(os.getenv("UPSTOX_CHAIN_CALLS_PER_POLL", "12"))
    kite_api_key: str = os.getenv("KITE_API_KEY", "")
    kite_api_secret: str = os.getenv("KITE_API_SECRET", "")
    kite_access_token: str = os.getenv("KITE_ACCESS_TOKEN", "")
    groww_totp_token: str = os.getenv("GROWW_TOTP_TOKEN", "")
    groww_totp_secret: str = os.getenv("GROWW_TOTP_SECRET", "")
    groww_access_token: str = os.getenv("GROWW_ACCESS_TOKEN", "")
    groww_oi_calls_per_poll: int = int(os.getenv("GROWW_OI_CALLS_PER_POLL", "60"))
    poll_seconds: int = int(os.getenv("POLL_SECONDS", "30"))
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    commentary_model: str = os.getenv("COMMENTARY_MODEL", "claude-sonnet-4-6")
    max_lots_per_order: int = int(os.getenv("MAX_LOTS_PER_ORDER", "5"))
    max_orders_per_day: int = int(os.getenv("MAX_ORDERS_PER_DAY", "20"))
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "data")))
    # ---- paper engine: charges (server/charges.py)
    charges_json: str = os.getenv("CHARGES_JSON", "")
    # ---- paper engine: liquidity classes (server/liquidity.py)
    liq_fut_accept_spread_pct: float = float(os.getenv("LIQ_FUT_ACCEPT_SPREAD_PCT", "0.05"))
    liq_fut_refuse_spread_pct: float = float(os.getenv("LIQ_FUT_REFUSE_SPREAD_PCT", "0.15"))
    liq_fut_accept_depth_pct: float = float(os.getenv("LIQ_FUT_ACCEPT_DEPTH_PCT", "25"))
    liq_fut_refuse_depth_pct: float = float(os.getenv("LIQ_FUT_REFUSE_DEPTH_PCT", "50"))
    liq_opt_accept_spread_pct: float = float(os.getenv("LIQ_OPT_ACCEPT_SPREAD_PCT", "3"))
    liq_opt_refuse_spread_pct: float = float(os.getenv("LIQ_OPT_REFUSE_SPREAD_PCT", "8"))
    liq_opt_accept_depth_pct: float = float(os.getenv("LIQ_OPT_ACCEPT_DEPTH_PCT", "20"))
    liq_opt_refuse_depth_pct: float = float(os.getenv("LIQ_OPT_REFUSE_DEPTH_PCT", "100"))
    liq_opt_min_oi_lots: float = float(os.getenv("LIQ_OPT_MIN_OI_LOTS", "50"))
    lottery_max_premium: float = float(os.getenv("LOTTERY_MAX_PREMIUM", "2"))
    lottery_max_sessions: int = int(os.getenv("LOTTERY_MAX_SESSIONS", "2"))
    # ---- paper engine: fills and the session calendar (server/fills.py, server/sessions.py)
    fill_tick: float = float(os.getenv("FILL_TICK", "0.05"))
    paper_queue_fill_at: str = os.getenv("PAPER_QUEUE_FILL_AT", "09:20")
    nse_holidays: str = os.getenv("NSE_HOLIDAYS", "")
    # ---- paper engine: ledger (server/paper.py)
    paper_capital: float = float(os.getenv("PAPER_CAPITAL", "500000"))
    margin_estimate_pct: float = float(os.getenv("MARGIN_ESTIMATE_PCT", "18"))

    @property
    def kite_ready(self) -> bool:
        return self.broker == "kite" and bool(self.kite_api_key and self.kite_access_token)

    @property
    def groww_ready(self) -> bool:
        return self.broker == "groww" and bool(self.groww_access_token or (self.groww_totp_token and self.groww_totp_secret))

    @property
    def kotak_data_ready(self) -> bool:
        return bool(self.kotak_consumer_key)

    @property
    def kotak_ready(self) -> bool:
        """Trading-capable: all five credentials, and Kotak chosen as the broker."""
        return self.broker == "kotak" and bool(self.kotak_consumer_key and self.kotak_mobile and self.kotak_ucc
                                                and self.kotak_totp_secret and self.kotak_mpin)

    @property
    def upstox_ready(self) -> bool:
        return self.data_provider == "upstox" and bool(self.upstox_analytics_token)

    @property
    def live_source(self) -> str | None:
        if self.upstox_ready:
            return "upstox"
        if self.data_provider == "kotak" and self.kotak_data_ready:
            return "kotak"
        if self.data_provider == "groww" and self.groww_ready:
            return "groww"
        if self.data_provider == "kite" and self.kite_ready:
            return "kite"
        if self.data_provider == "fake":
            return "fake"
        return None

    @property
    def live_enabled(self) -> bool:
        return self.live_source is not None

    @property
    def orders_enabled(self) -> bool:
        # off unless ORDERS=true; then paper orders always work and real orders need a configured broker
        return self.orders and (self.paper or self.kite_ready or self.groww_ready or self.kotak_ready)

    @property
    def commentary_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    def public(self) -> dict:
        """What the page is told about the server (never secrets)."""
        return {"live": self.live_enabled, "live_source": self.live_source, "orders": self.orders_enabled, "paper": self.paper,
                "commentary": self.commentary_enabled, "verdict": self.commentary_enabled, "broker": self.broker if self.orders_enabled else "none",
                "max_lots": self.max_lots_per_order, "poll_seconds": self.poll_seconds}


settings = Settings()
