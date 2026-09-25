"""v84 runtime: stable v80 base with canonical automation-option sync and improved real rebalancing selection."""
import json
import os

import v80_main as base
from automation_v67 import AutomationControllerV67, DEFAULTS as AUTOMATION_DEFAULTS
from controlled_learning import ControlledLearning
from news_learning import NewsLearning
from real_autonomous_v81 import RealPortfolioAllocatorV81, install_real_settings
from real_autonomous_v82 import secret_hash

app = base.app
legacy = base.legacy

AUTOMATION_KEYS = tuple(AUTOMATION_DEFAULTS.keys())
REAL_OPTION_KEYS = (
    'real_trading_enabled','real_kill_switch','real_fee_bps','real_fx_fee_bps','real_slippage_bps',
    'real_max_price_deviation_pct','real_allow_fx_conversion','real_max_order_volume','real_max_order_notional_eur',
    'real_allowed_symbols','real_allow_market_orders','real_max_orders_per_day','real_max_fx_orders_per_day',
    'real_balancing_enabled','real_balancing_execute_enabled','real_balancing_dry_run',
    'real_balancing_interval_minutes','real_balancing_max_position_pct','real_balancing_cash_reserve_pct',
    'real_balancing_min_trade_eur','real_balancing_max_trade_eur','real_balancing_no_trade_band_pct',
    'real_balancing_max_actions_per_run','real_balancing_max_actions_per_day','real_balancing_cooldown_hours',
    'real_balancing_minimum_score','real_balancing_limit_offset_pct',
)


def _options():
    path = os.environ.get("APP_OPTIONS", "/data/options.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, ValueError, TypeError):
        return {}


def _sync_options(db, options):
    """Treat explicit add-on options as the startup source of truth.

    Existing database rows must not permanently mask changed Home Assistant
    add-on options. The automation execution flag is especially important:
    a stale false row otherwise survives every restart.
    """
    changed = []
    for key in AUTOMATION_KEYS + REAL_OPTION_KEYS:
        if key not in options:
            continue
        value = options.get(key)
        if isinstance(value, bool):
            normalized = "true" if value else "false"
        else:
            normalized = str(value).lower() if isinstance(value, str) else str(value)
        if db.value(key, "") != normalized:
            db.set(key, normalized)
            changed.append(key)
    return changed


def install_real_settings_v84(db, options=None):
    options = options or {}
    install_real_settings(db, options)
    _sync_options(db, options)
    if "real_balancing_automation_secret" not in options:
        return

    secret = str(options.get("real_balancing_automation_secret") or "")
    current = str(db.value("real_balancing_automation_secret", "") or "")
    current_hash = str(db.value("real_balancing_automation_secret_hash", "") or "")
    expected = secret_hash(secret)

    if secret == current:
        if current_hash != expected:
            db.set_setting("real_balancing_automation_secret_hash", expected)
        return

    db.set_setting("real_balancing_automation_secret", secret)
    db.set_setting("real_balancing_automation_secret_hash", expected)
    db.audit(
        "REAL_AUTOMATION_SECRET_ROTATED" if secret else "REAL_AUTOMATION_SECRET_REVOKED",
        "Automation secret configuration changed; only its internal hash is stored.",
        "warning",
        "REAL",
    )


options = _options()
install_real_settings_v84(legacy.db, options)

allocator = RealPortfolioAllocatorV81(legacy.db, legacy.real_trade_engine)
legacy.real_allocator = allocator

controller = AutomationControllerV67(
    legacy.db,
    legacy.pipeline,
    legacy.news_prefilter,
    ControlledLearning(legacy.db),
    NewsLearning(legacy.db),
    legacy.run_paper_cycle,
    allocator,
)
controller.start_background()
base.controller = controller
legacy.controller = controller

legacy.NAV_ITEMS = [
    ("/", "Übersicht"), ("/products", "Märkte & Produkte"),
    ("/scanner", "Analyse & Research"), ("/portfolio", "Portfolio"),
    ("/paper", "Paper-Trading"), ("/controlled-learning", "Kontrolliertes Lernen"),
    ("/news-learning", "Nachrichten & AI"), ("/automatik", "Automatik"),
    ("/backtests", "Evaluation & Backtests"), ("/data-quality", "Datenqualität"),
    ("/fees", "Gebühren & Kosten"), ("/process", "Systemablauf"),
    ("/real-trading", "Realhandel"), ("/decision-matrix", "Regelmatrix"),
    ("/tax-info", "Steuerinfo AT"), ("/settings", "Einstellungen"),
    ("/api", "API & Verbindungen"), ("/audit", "Audit & Ereignisse"),
]


@app.get("/v84-health")
def v84_health():
    cfg = controller.settings()
    return {
        "version": "0.1.0-dev.84",
        "runtime": "v84_main",
        "real_trading_enabled": legacy.db.value("real_trading_enabled", "false").lower() == "true",
        "real_kill_switch": legacy.db.value("real_kill_switch", "true").lower() == "true",
        "real_balancing_enabled": legacy.db.value("real_balancing_enabled", "false").lower() == "true",
        "real_balancing_execute_enabled": legacy.db.value("real_balancing_execute_enabled", "false").lower() == "true",
        "automation_secret_configured": bool(legacy.db.value("real_balancing_automation_secret_hash", "")),
        "automation_options_synced": [
            key for key in AUTOMATION_KEYS
            if key in options
        ],
        "automation": cfg,
        "recent_real_runs": controller.latest(20),
    }


@app.get("/v83-health")
def v83_health_compat():
    return v84_health()


@app.get("/v82-health")
def v82_health_compat():
    return v84_health()


app.view_functions["v81_health"] = v82_health_compat
