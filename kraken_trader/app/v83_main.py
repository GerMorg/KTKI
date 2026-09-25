"""v83 runtime: stable v80 base with repaired autonomous controller wiring.

v83 deliberately does not import v81/v82 runtime modules. Those runtimes inherit
from earlier entrypoints whose public controller attribute is not guaranteed to
exist. The active runtime wires the controller directly from the canonical
v80 legacy state.
"""
import hashlib
import json
import os

import v80_main as base
from automation_v67 import AutomationControllerV67
from controlled_learning import ControlledLearning
from news_learning import NewsLearning
from real_autonomous_v81 import RealPortfolioAllocatorV81, install_real_settings
from real_autonomous_v82 import secret_hash

app = base.app
legacy = base.legacy


def _options():
    path = os.environ.get("APP_OPTIONS", "/data/options.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, ValueError, TypeError):
        return {}


def install_real_settings_v83(db, options=None):
    options = options or {}
    install_real_settings(db, options)
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


install_real_settings_v83(legacy.db, _options())

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


@app.get("/v83-health")
def v83_health():
    cfg = controller.settings()
    return {
        "version": "0.1.0-dev.83",
        "runtime": "v83_main",
        "real_trading_enabled": legacy.db.value("real_trading_enabled", "false").lower() == "true",
        "real_kill_switch": legacy.db.value("real_kill_switch", "true").lower() == "true",
        "real_balancing_enabled": legacy.db.value("real_balancing_enabled", "false").lower() == "true",
        "real_balancing_execute_enabled": legacy.db.value("real_balancing_execute_enabled", "false").lower() == "true",
        "automation_secret_configured": bool(legacy.db.value("real_balancing_automation_secret_hash", "")),
        "automation": cfg,
        "recent_real_runs": controller.latest(20),
    }


@app.get("/v82-health")
def v82_health_compat():
    return v83_health()


app.view_functions["v81_health"] = v82_health_compat
