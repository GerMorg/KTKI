"""v88 runtime: v87 real-trading diagnostics with explicit submission evidence."""
import v87_main as base

app = base.app
legacy = base.legacy
controller = base.controller
options = getattr(base, "options", {})


def v88_health():
    payload = base.v87_health()
    payload = {**payload, "version": "0.1.0-dev.88", "runtime": "v88_main"}
    return payload


if "v88_health" not in app.view_functions:
    app.add_url_rule("/v88-health", "v88_health", v88_health)
