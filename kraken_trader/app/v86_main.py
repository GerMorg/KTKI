"""v86 runtime: stable v84 application entrypoint with isolated real-path diagnostics.

The application startup path intentionally delegates only to the already verified
v84 runtime. Diagnostic helpers are defined here without importing additional
runtime modules, so a diagnostic failure cannot prevent Flask/Gunicorn startup.
"""
import hashlib
import hmac

import v84_main as base

app = base.app
legacy = base.legacy
controller = base.controller
options = getattr(base, "options", {})


def _secret_matches(secret, stored_hash):
    expected = hashlib.sha256(str(secret or "").encode()).hexdigest() if secret else ""
    actual = str(stored_hash or "")
    return bool(expected and actual) and hmac.compare_digest(expected, actual)


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
        "automation_secret_configured": bool(
            legacy.db.value("real_balancing_automation_secret_hash", "")
        ),
        "automation_secret_matches": False,
    }
    secret = legacy.db.value("real_balancing_automation_secret", "")
    stored_hash = legacy.db.value("real_balancing_automation_secret_hash", "")
    out["automation_secret_matches"] = _secret_matches(secret, stored_hash)

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


@app.get("/v86-health")
def v86_health():
    cfg = controller.settings()
    preflight = _api_preflight()
    real_cfg = legacy.real_allocator.settings()
    recent = controller.latest(50)
    blockers = []

    if not preflight["api_key_configured"]:
        blockers.append("KRAKEN_API_KEY_MISSING")
    if not preflight["api_secret_configured"]:
        blockers.append("KRAKEN_API_SECRET_MISSING")
    if not preflight["private_balance_ok"]:
        blockers.append("KRAKEN_PRIVATE_API_UNAVAILABLE")
    if not preflight["kill_switch_clear"]:
        blockers.append("REAL_KILL_SWITCH_ACTIVE")
    if not preflight["automation_secret_matches"]:
        blockers.append("AUTOMATION_SECRET_INVALID")
    if not real_cfg["enabled"]:
        blockers.append("REAL_BALANCING_DISABLED")
    if not real_cfg["automatic_execution"]:
        blockers.append("REAL_EXECUTION_DISABLED")
    if real_cfg["dry_run"]:
        blockers.append("REAL_DRY_RUN")

    return {
        "version": "0.1.0-dev.86",
        "runtime": "v86_main",
        "automation": cfg,
        "real": real_cfg,
        "api_preflight": preflight,
        "blockers": blockers,
        "recent_real_runs": [
            x for x in recent
            if str(x.get("subsystem", "")).lower() == "real"
        ][:20],
        "recent_automation_runs": recent[:20],
    }


# Compatibility endpoints: v84 already registered several legacy routes on the
# shared Flask app. Reusing their endpoint mappings avoids Flask's duplicate
# endpoint assertion during Gunicorn import.
for _endpoint in ("v84_health", "v83_health_compat", "v82_health_compat", "v81_health"):
    if _endpoint in app.view_functions:
        app.view_functions[_endpoint] = v86_health

if "v85_health_compat" in app.view_functions:
    app.view_functions["v85_health_compat"] = v86_health
else:
    app.add_url_rule("/v85-health", "v85_health_compat", v86_health)
