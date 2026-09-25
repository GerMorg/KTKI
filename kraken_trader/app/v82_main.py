"""v82 runtime: clean automation-secret lifecycle and autonomous real execution.

The user-facing configuration exposes only one automation secret. The hash is
managed internally and is never exposed through health/status endpoints.
"""
import hashlib
import hmac
import json
import os

import v81_main as base
from real_autonomous_v81 import install_real_settings as _install_v81

app = base.app
legacy = base.legacy
allocator = legacy.real_allocator
controller = base.controller


def _options():
    path = os.environ.get("APP_OPTIONS", "/data/options.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, ValueError, TypeError):
        return {}


def install_real_settings_v82(db, options=None):
    options = options or {}
    # Preserve all v81 defaults and internal settings.
    _install_v81(db, options)

    # The HA option is authoritative when present, including an explicit
    # empty value. This makes secret rotation and revocation deterministic.
    if "real_balancing_automation_secret" not in options:
        return

    secret = str(options.get("real_balancing_automation_secret") or "")
    current = str(db.value("real_balancing_automation_secret") or "")
    current_hash = str(db.value("real_balancing_automation_secret_hash") or "")

    if secret == current:
        expected = hashlib.sha256(secret.encode()).hexdigest() if secret else ""
        if current_hash != expected:
            db.set_setting("real_balancing_automation_secret_hash", expected)
        return

    db.set_setting("real_balancing_automation_secret", secret)
    new_hash = hashlib.sha256(secret.encode()).hexdigest() if secret else ""
    db.set_setting("real_balancing_automation_secret_hash", new_hash)
    db.audit(
        "REAL_AUTOMATION_SECRET_ROTATED" if secret else "REAL_AUTOMATION_SECRET_REVOKED",
        "Automation secret configuration changed; only its internal hash is exposed to the runtime.",
        "warning",
        "REAL",
    )


install_real_settings_v82(legacy.db, _options())


@app.get("/v82-health")
def v82_health():
    cfg = controller.settings() if controller else {}
    configured = bool(legacy.db.value("real_balancing_automation_secret_hash", ""))
    return {
        "version": "0.1.0-dev.82",
        "runtime": "v82_main",
        "real_trading_enabled": legacy.db.value("real_trading_enabled", "false").lower() == "true",
        "real_kill_switch": legacy.db.value("real_kill_switch", "true").lower() == "true",
        "real_balancing_enabled": legacy.db.value("real_balancing_enabled", "false").lower() == "true",
        "real_balancing_execute_enabled": legacy.db.value("real_balancing_execute_enabled", "false").lower() == "true",
        "automation_secret_configured": configured,
        "automation": cfg,
        "recent_real_runs": controller.latest(20) if controller else [],
    }


# Keep the v81 diagnostic endpoint compatible while making v82 the reported
# runtime. No secret or hash is ever returned.
@app.get("/v81-health")
def v81_health_compat():
    return v82_health()
