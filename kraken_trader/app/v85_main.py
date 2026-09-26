"""v85 runtime: verified real-execution path, Kraken API preflight and autonomous rebalancing diagnostics."""
import json
import os
import traceback

import v84_main as base
from real_autonomous_v82 import secret_matches

app = base.app
legacy = base.legacy
controller = base.controller
options = getattr(base, "options", {})


def _api_preflight():
    client = legacy.client
    out = {
        "api_key_configured": bool(getattr(client, "key", "")),
        "api_secret_configured": bool(getattr(client, "secret", "")),
        "private_balance_ok": False,
        "private_balance_error": None,
        "private_balance_assets": 0,
        "real_engine_enabled": bool(legacy.real_trade_engine.enabled()),
        "kill_switch_clear": legacy.db.value("real_kill_switch", "true").lower() != "true",
        "automation_secret_configured": bool(legacy.db.value("real_balancing_automation_secret_hash", "")),
        "automation_secret_matches": False,
    }
    secret = legacy.db.value("real_balancing_automation_secret", "")
    stored_hash = legacy.db.value("real_balancing_automation_secret_hash", "")
    out["automation_secret_matches"] = secret_matches(secret, stored_hash)
    if not out["api_key_configured"] or not out["api_secret_configured"]:
        out["private_balance_error"] = "Kraken API key/secret fehlt"
        return out
    try:
        balances = client.balance() or {}
        out["private_balance_ok"] = isinstance(balances, dict)
        out["private_balance_assets"] = len(balances) if isinstance(balances, dict) else 0
        if not out["private_balance_ok"]:
            out["private_balance_error"] = "Balance-Antwort ist kein Objekt"
    except Exception as exc:
        out["private_balance_error"] = type(exc).__name__ + ": " + str(exc)[:400]
    return out


@app.get("/v85-health")
def v85_health():
    cfg = controller.settings()
    preflight = _api_preflight()
    real_cfg = legacy.real_allocator.settings()
    recent = controller.latest(50)
    real_runs = [x for x in recent if str(x.get("subsystem", "")).lower() == "real"]
    blockers = []
    if not preflight["api_key_configured"]: blockers.append("KRAKEN_API_KEY_MISSING")
    if not preflight["api_secret_configured"]: blockers.append("KRAKEN_API_SECRET_MISSING")
    if not preflight["private_balance_ok"]: blockers.append("KRAKEN_PRIVATE_API_UNAVAILABLE")
    if not preflight["kill_switch_clear"]: blockers.append("REAL_KILL_SWITCH_ACTIVE")
    if not preflight["automation_secret_matches"]: blockers.append("AUTOMATION_SECRET_INVALID")
    if not real_cfg["enabled"]: blockers.append("REAL_BALANCING_DISABLED")
    if not real_cfg["automatic_execution"]: blockers.append("REAL_EXECUTION_DISABLED")
    if real_cfg["dry_run"]: blockers.append("REAL_DRY_RUN")
    return {
        "version": "0.1.0-dev.85",
        "runtime": "v85_main",
        "automation": cfg,
        "real": real_cfg,
        "api_preflight": preflight,
        "blockers": blockers,
        "recent_real_runs": real_runs[:20],
        "recent_automation_runs": recent[:20],
    }


@app.get("/v84-health")
def v84_health_compat():
    return v85_health()

@app.get("/v83-health")
def v83_health_compat():
    return v85_health()

@app.get("/v82-health")
def v82_health_compat():
    return v85_health()

app.view_functions["v81_health"] = v82_health_compat
